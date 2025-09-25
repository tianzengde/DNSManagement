"""服务商管理API"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from tortoise.transactions import atomic
from app.models import Provider
from app.schemas import ProviderCreate, ProviderUpdate, ProviderResponse
from app.providers import HuaweiProvider, AliyunProvider
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/", response_model=List[ProviderResponse])
async def get_providers():
    """获取服务商列表"""
    providers = await Provider.all().prefetch_related()
    return providers


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: int):
    """获取单个服务商"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    return provider


@router.post("/", response_model=ProviderResponse)
@atomic()
async def create_provider(provider_data: ProviderCreate):
    """创建服务商"""
    # 测试连接
    if provider_data.type.value == 1:  # 华为云
        provider_instance = HuaweiProvider(
            provider_data.access_key,
            provider_data.secret_key,
            provider_data.region or ""
        )
    elif provider_data.type.value == 2:  # 阿里云
        provider_instance = AliyunProvider(
            provider_data.access_key,
            provider_data.secret_key,
            provider_data.region or ""
        )
    else:
        raise HTTPException(status_code=400, detail="不支持的服务商类型")
    
    # 创建服务商（先保存数据）
    provider = await Provider.create(**provider_data.dict())
    
    # 测试连接（可选，不影响创建）
    if not (provider_data.access_key.startswith("demo_") and provider_data.secret_key.startswith("demo_")):
        try:
            if await provider_instance.test_connection():
                # 连接成功，保持启用状态
                pass
            else:
                # 连接失败，但数据已保存
                pass
        except Exception as e:
            # 连接测试失败，但数据已保存，可以通过后续的测试连接功能来验证
            pass
    
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
@atomic()
async def update_provider(provider_id: int, provider_data: ProviderUpdate):
    """更新服务商"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    # 只更新提供的字段
    update_data = provider_data.dict(exclude_unset=True)
    
    # 如果有密钥更新，测试连接
    if provider_data.access_key or provider_data.secret_key:
        access_key = provider_data.access_key or provider.access_key
        secret_key = provider_data.secret_key or provider.secret_key
        region = provider_data.region or provider.region
        
        if provider.type.value == 1:  # 华为云
            provider_instance = HuaweiProvider(access_key, secret_key, region or "")
        elif provider.type.value == 2:  # 阿里云
            provider_instance = AliyunProvider(access_key, secret_key, region or "")
        else:
            raise HTTPException(status_code=400, detail="不支持的服务商类型")
        
        if not await provider_instance.test_connection():
            raise HTTPException(status_code=400, detail="连接测试失败，请检查配置")
    
    # 更新数据库
    await provider.update_from_dict(update_data)
    await provider.save()
    return provider


@router.delete("/{provider_id}")
@atomic()
async def delete_provider(provider_id: int):
    """删除服务商"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    # 检查是否有关联的域名
    domain_count = await provider.domains.all().count()
    if domain_count > 0:
        raise HTTPException(status_code=400, detail=f"该服务商下还有 {domain_count} 个域名，无法删除")
    
    await provider.delete()
    return {"message": "删除成功"}


@router.post("/{provider_id}/test")
async def test_provider_connection(provider_id: int):
    """测试服务商连接"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    try:
        if provider.type.value == 1:  # 华为云
            provider_instance = HuaweiProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        elif provider.type.value == 2:  # 阿里云
            provider_instance = AliyunProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的服务商类型")
        
        success = await provider_instance.test_connection()
        
        # 更新状态和测试时间
        from datetime import datetime
        provider.status = "connected" if success else "failed"
        provider.last_test_at = datetime.now()
        await provider.save()
        
        return {
            "success": success, 
            "message": "连接成功" if success else "连接失败",
            "status": provider.status,
            "last_test_at": provider.last_test_at
        }
    except Exception as e:
        # 更新失败状态
        from datetime import datetime
        provider.status = "error"
        provider.last_test_at = datetime.now()
        await provider.save()
        
        return {
            "success": False, 
            "message": f"连接测试失败: {str(e)}",
            "status": provider.status,
            "last_test_at": provider.last_test_at
        }


@router.get("/{provider_id}/domains")
async def get_provider_domains(provider_id: int):
    """获取服务商下的域名列表"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    try:
        if provider.type.value == 1:  # 华为云
            provider_instance = HuaweiProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        elif provider.type.value == 2:  # 阿里云
            provider_instance = AliyunProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的服务商类型")
        
        domains = await provider_instance.get_domains()
        
        # 获取所有域名的记录
        result = []
        for domain in domains:
            domain_name = domain["name"]
            try:
                # 获取该域名的所有记录
                records = await provider_instance.get_records(domain_name)
                for record in records:
                    result.append({
                        "name": record["name"],
                        "domain": domain_name,
                        "provider_name": provider.name,
                        "type": record.get("type"),
                        "records": record.get("records", []),
                        "ttl": record.get("ttl"),
                        "status": record.get("status"),
                        "zone_id": record.get("zone_id", ""),
                        "record_id": record.get("id", "")
                    })
            except Exception as e:
                # 如果获取记录失败，至少显示域名信息
                result.append({
                    "name": domain_name,
                    "domain": domain_name,
                    "provider_name": provider.name,
                    "type": "DOMAIN",
                    "records": [],
                    "ttl": "-",
                    "status": "UNKNOWN",
                    "zone_id": "",
                    "record_id": "",
                    "error": str(e)
                })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取域名列表失败: {str(e)}")


@router.get("/{provider_id}/domains/{domain_name}/records")
async def get_domain_records(provider_id: int, domain_name: str):
    """获取指定域名的解析记录"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    try:
        if provider.type.value == 1:  # 华为云
            provider_instance = HuaweiProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        elif provider.type.value == 2:  # 阿里云
            provider_instance = AliyunProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的服务商类型")
        
        records = await provider_instance.get_records(domain_name)
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取域名记录失败: {str(e)}")


@router.delete("/{provider_id}/records/{record_name}")
async def delete_dns_record(provider_id: int, record_name: str):
    """删除DNS记录"""
    provider = await Provider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    try:
        if provider.type.value == 1:  # 华为云
            provider_instance = HuaweiProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        elif provider.type.value == 2:  # 阿里云
            provider_instance = AliyunProvider(
                provider.access_key,
                provider.secret_key,
                provider.region or ""
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的服务商类型")
        
        # 先获取记录信息
        records = await provider_instance.get_records(record_name)
        if not records:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        # 删除记录
        success = await provider_instance.delete_record(record_name, records[0]["type"])
        if success:
            return {"message": "记录删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除记录失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记录失败: {str(e)}")


@router.post("/{provider_id}/sync")
async def sync_provider_domains(provider_id: int):
    """手动同步服务商域名"""
    try:
        # 检查服务商是否存在
        provider = await Provider.get(id=provider_id)
        
        # 添加手动同步任务
        scheduler_service.add_manual_sync_job(provider_id)
        
        return {"message": "同步任务已启动，请稍后查看结果"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动同步任务失败: {str(e)}")


@router.get("/sync/status")
async def get_sync_status():
    """获取同步任务状态"""
    try:
        jobs = scheduler_service.get_jobs()
        job_info = []
        for job in jobs:
            job_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return {"jobs": job_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")
