"""DDNS管理API"""
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from tortoise.transactions import atomic
from datetime import datetime, timedelta
from app.models import DDNSConfig, DDNSLog, Domain, DNSRecord, RecordType
from app.schemas import (
    DDNSConfigCreate, DDNSConfigUpdate, DDNSConfigResponse, 
    DDNSLogResponse, DDNSUpdateRequest, DDNSUpdateResponse
)
from app.providers import HuaweiProvider, AliyunProvider
from app.providers.base import get_provider_instance
import logging

router = APIRouter(prefix="/api/ddns", tags=["ddns"])
logger = logging.getLogger(__name__)


async def get_public_ip(ip_version=4):
    """获取公网IP地址"""
    if ip_version == 4:
        ip_services = [
            "https://api.ipify.org",
            "https://ipv4.icanhazip.com",
            "https://api.ip.sb/ip",
            "https://ifconfig.me/ip",
            "https://checkip.amazonaws.com"
        ]
    else:  # IPv6
        ip_services = [
            "https://ipv6.icanhazip.com",
            "https://api6.ipify.org",
            "https://ifconfig.me/ip"
        ]
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service in ip_services:
            try:
                response = await client.get(service)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip_version == 4:
                        # 验证IPv4格式
                        parts = ip.split('.')
                        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                            return ip
                    else:
                        # 简单验证IPv6格式（包含冒号）
                        if ':' in ip:
                            return ip
            except Exception as e:
                logger.debug(f"获取IP失败 {service}: {e}")
                continue
    
    return None  # 返回None而不是抛出异常，让调用者处理


@router.get("/", response_model=List[DDNSConfigResponse])
async def get_ddns_configs():
    """获取DDNS配置列表"""
    configs = await DDNSConfig.all().prefetch_related('domain__provider')
    return configs


@router.get("/{config_id}", response_model=DDNSConfigResponse)
async def get_ddns_config(config_id: int):
    """获取单个DDNS配置"""
    config = await DDNSConfig.get_or_none(id=config_id).prefetch_related('domain__provider')
    if not config:
        raise HTTPException(status_code=404, detail="DDNS配置不存在")
    return config


@router.post("/", response_model=DDNSConfigResponse)
async def create_ddns_config(config_data: DDNSConfigCreate):
    """创建DDNS配置"""
    # 验证域名是否存在
    domain = await Domain.get_or_none(id=config_data.domain_id).prefetch_related('provider')
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 验证子域名格式
    if not config_data.subdomain or not config_data.subdomain.strip():
        raise HTTPException(status_code=400, detail="子域名不能为空")
    
    # 验证子域名是否属于指定域名
    if not config_data.subdomain.endswith(f".{domain.name}") and config_data.subdomain != domain.name:
        raise HTTPException(status_code=400, detail=f"子域名必须属于域名 {domain.name}")
    
    # 检查DNS解析记录是否已存在
    existing_record = await DNSRecord.get_or_none(
        domain_id=config_data.domain_id,
        name=config_data.subdomain,
        type=config_data.record_type
    )
    if existing_record:
        raise HTTPException(status_code=400, detail="该DNS解析记录已存在，请先删除现有记录")
    
    # 检查是否已存在相同的DDNS配置
    existing_ddns_config = await DDNSConfig.get_or_none(
        domain_id=config_data.domain_id,
        subdomain=config_data.subdomain
    )
    if existing_ddns_config:
        raise HTTPException(status_code=400, detail="该子域名已存在DDNS配置，请先删除现有配置")
    
    # 验证更新间隔
    if config_data.update_interval < 60:
        raise HTTPException(status_code=400, detail="更新间隔不能少于60秒")
    
    # 获取服务商实例
    provider_instance = get_provider_instance(domain.provider)
    if not provider_instance:
        raise HTTPException(status_code=400, detail="服务商配置错误")
    
    # 获取当前公网IP（这是网络操作，不应该在事务中）
    try:
        if config_data.record_type == 1:  # A记录
            current_ip = await get_public_ip()
        else:  # AAAA记录
            current_ip = await get_public_ip(ip_version=6)
        
        if not current_ip:
            raise HTTPException(status_code=400, detail="无法获取公网IP地址")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取公网IP失败: {str(e)}")
    
    # 准备DNS记录数据
    record_data = {
        'name': config_data.subdomain,
        'type': 'A' if config_data.record_type == 1 else 'AAAA',
        'value': current_ip,
        'ttl': 300
    }
    
    # 调用服务商API创建记录（这是网络操作，不应该在事务中）
    try:
        external_id = await provider_instance.add_record(domain.name, record_data)
        if not external_id:
            raise HTTPException(status_code=400, detail="服务商API返回的记录ID为空")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建DNS记录失败: {str(e)}")
    
    # 只有数据库操作才使用事务
    try:
        from tortoise.transactions import in_transaction
        async with in_transaction():
            # 创建本地DNS记录
            await DNSRecord.create(
                domain_id=config_data.domain_id,
                name=config_data.subdomain,
                type=config_data.record_type,
                value=current_ip,
                ttl=300,
                external_id=external_id,
                enabled=True
            )
            
            # 创建本地DDNS配置
            config_dict = config_data.dict()
            config_dict['last_ip'] = current_ip
            config_dict['last_update_at'] = datetime.now()
            
            config = await DDNSConfig.create(**config_dict)
            
            # 添加DDNS日志
            await DDNSLog.create(
                ddns_config=config,
                old_ip=None,
                new_ip=current_ip,
                status="success",
                message=f"DDNS配置创建成功，设置初始IP: {current_ip}"
            )
            
    except Exception as e:
        # 如果数据库操作失败，尝试删除已创建的DNS记录
        try:
            await provider_instance.delete_record(domain.name, external_id)
        except:
            pass  # 删除失败也不影响错误返回
        raise HTTPException(status_code=400, detail=f"创建DDNS配置失败: {str(e)}")
    
    await config.fetch_related('domain__provider')
    return config


@router.put("/{config_id}", response_model=DDNSConfigResponse)
@atomic()
async def update_ddns_config(config_id: int, config_data: DDNSConfigUpdate):
    """更新DDNS配置"""
    config = await DDNSConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="DDNS配置不存在")
    
    # 更新数据
    update_data = config_data.dict(exclude_unset=True)
    
    # 验证更新间隔
    if 'update_interval' in update_data and update_data['update_interval'] < 60:
        raise HTTPException(status_code=400, detail="更新间隔不能少于60秒")
    
    # 如果修改了子域名，检查是否冲突
    if 'subdomain' in update_data:
        # 验证子域名是否属于指定域名
        domain = await Domain.get_or_none(id=config.domain_id)
        if domain and not update_data['subdomain'].endswith(f".{domain.name}") and update_data['subdomain'] != domain.name:
            raise HTTPException(status_code=400, detail=f"子域名必须属于域名 {domain.name}")
        
        existing_config = await DDNSConfig.get_or_none(
            domain_id=config.domain_id,
            subdomain=update_data['subdomain']
        ).exclude(id=config_id)
        if existing_config:
            raise HTTPException(status_code=400, detail="该域名下已存在相同的子域名配置")
    
    await config.update_from_dict(update_data)
    await config.save()
    await config.fetch_related('domain__provider')
    
    return config


@router.delete("/{config_id}")
@atomic()
async def delete_ddns_config(config_id: int):
    """删除DDNS配置"""
    config = await DDNSConfig.get_or_none(id=config_id).prefetch_related('domain__provider')
    if not config:
        raise HTTPException(status_code=404, detail="DDNS配置不存在")
    
    # 尝试删除对应的DNS记录
    try:
        # 查找对应的DNS记录
        dns_record = await DNSRecord.get_or_none(
            domain_id=config.domain_id,
            name=config.subdomain,
            type=config.record_type
        )
        
        if dns_record:
            # 获取服务商实例
            provider_instance = get_provider_instance(config.domain.provider)
            if provider_instance:
                # 删除DNS记录
                await provider_instance.delete_record(config.domain.name, dns_record.external_id)
                # 删除本地DNS记录
                await dns_record.delete()
    except Exception as e:
        # 删除DNS记录失败，记录日志但不阻止DDNS配置删除
        logger.warning(f"删除DNS记录失败: {str(e)}")
    
    # 删除相关日志
    await DDNSLog.filter(ddns_config=config).delete()
    await config.delete()
    
    return {"message": "删除成功"}


@router.get("/{config_id}/logs")
async def get_ddns_logs(
    config_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页记录数")
):
    """获取DDNS更新日志"""
    config = await DDNSConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="DDNS配置不存在")
    
    # 计算偏移量
    offset = (page - 1) * page_size
    
    # 获取总记录数
    total = await DDNSLog.filter(ddns_config=config).count()
    
    # 获取分页日志
    logs = await DDNSLog.filter(ddns_config=config).order_by('-created_at').offset(offset).limit(page_size)
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "logs": logs,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.post("/{config_id}/update", response_model=DDNSUpdateResponse)
async def update_ddns_record(config_id: int, force: bool = False):
    """手动更新DDNS记录"""
    config = await DDNSConfig.get_or_none(id=config_id).prefetch_related('domain__provider')
    if not config:
        raise HTTPException(status_code=404, detail="DDNS配置不存在")
    
    if not config.enabled and not force:
        raise HTTPException(status_code=400, detail="DDNS配置已禁用")
    
    # 获取当前公网IP（网络操作，不在事务中）
    try:
        current_ip = await get_public_ip()
    except Exception as e:
        # 记录获取IP失败的日志
        try:
            from tortoise.transactions import in_transaction
            async with in_transaction():
                await DDNSLog.create(
                    ddns_config=config,
                    old_ip=config.last_ip,
                    new_ip=None,
                    status="failed",
                    message=f"获取公网IP失败: {str(e)}"
                )
        except:
            pass
        
        return DDNSUpdateResponse(
            success=False,
            message=f"获取公网IP失败: {str(e)}",
            old_ip=config.last_ip,
            new_ip=None
        )
    
    old_ip = config.last_ip
    ip_changed = (config.last_ip != current_ip)
    
    # 检查IP是否有变化
    if not force and not ip_changed:
        # IP未变化，记录日志但不更新DNS
        try:
            from tortoise.transactions import in_transaction
            async with in_transaction():
                await DDNSLog.create(
                    ddns_config=config,
                    old_ip=old_ip,
                    new_ip=current_ip,
                    status="success",
                    message="IP地址未变化，无需更新"
                )
        except:
            pass
        
        return DDNSUpdateResponse(
            success=True,
            message="IP地址未变化，无需更新",
            old_ip=old_ip,
            new_ip=current_ip
        )
    
    # 构建完整域名
    full_domain = f"{config.subdomain}.{config.domain.name}"
    
    # 获取服务商实例
    provider_instance = get_provider_instance(config.domain.provider)
    if not provider_instance:
        # 记录服务商错误日志
        try:
            from tortoise.transactions import in_transaction
            async with in_transaction():
                await DDNSLog.create(
                    ddns_config=config,
                    old_ip=old_ip,
                    new_ip=current_ip,
                    status="failed",
                    message="不支持的服务商类型"
                )
        except:
            pass
        
        return DDNSUpdateResponse(
            success=False,
            message="不支持的服务商类型",
            old_ip=old_ip,
            new_ip=current_ip
        )
    
    # 查找现有的DNS记录
    existing_record = await DNSRecord.get_or_none(
        domain=config.domain,
        name=full_domain,
        type=config.record_type
    )
    
    success = False
    error_message = None
    
    # 执行DNS更新（网络操作，不在事务中）
    try:
        if existing_record:
            # 更新现有记录
            record_data = {
                "name": full_domain,
                "type": "A" if config.record_type == RecordType.A else "AAAA",
                "value": current_ip,
                "ttl": existing_record.ttl
            }
            
            success = await provider_instance.update_record(
                config.domain.name,
                existing_record.external_id,
                record_data
            )
        else:
            # 创建新记录
            record_data = {
                "name": full_domain,
                "type": "A" if config.record_type == RecordType.A else "AAAA",
                "value": current_ip,
                "ttl": 600
            }
            
            external_id = await provider_instance.add_record(config.domain.name, record_data)
            success = bool(external_id)
            
    except Exception as e:
        error_message = str(e)
        success = False
    
    # 只有数据库操作才使用事务
    try:
        from tortoise.transactions import in_transaction
        async with in_transaction():
            if success:
                if existing_record:
                    # 更新现有记录
                    existing_record.value = current_ip
                    await existing_record.save()
                else:
                    # 创建新的DNS记录
                    await DNSRecord.create(
                        domain=config.domain,
                        name=full_domain,
                        type=config.record_type,
                        value=current_ip,
                        ttl=600,
                        external_id=external_id
                    )
                
                # 更新配置
                config.last_ip = current_ip
                config.last_update_at = datetime.now()
                await config.save()
            
            # 记录日志
            log_status = "success" if success else "failed"
            log_message = "DDNS更新成功" if success else (error_message or "DDNS更新失败")
            
            await DDNSLog.create(
                ddns_config=config,
                old_ip=old_ip,
                new_ip=current_ip,
                status=log_status,
                message=log_message
            )
    except Exception as e:
        error_message = f"数据库操作失败: {str(e)}"
        success = False
    
    # 返回结果
    if success:
        return DDNSUpdateResponse(
            success=True,
            message="DDNS更新成功",
            old_ip=old_ip,
            new_ip=current_ip,
            updated_at=config.last_update_at
        )
    else:
        return DDNSUpdateResponse(
            success=False,
            message=error_message or "DDNS更新失败",
            old_ip=old_ip,
            new_ip=current_ip
        )


@router.post("/update-all")
async def update_all_ddns():
    """批量更新所有启用的DDNS配置"""
    configs = await DDNSConfig.filter(enabled=True).prefetch_related('domain__provider')
    
    if not configs:
        return {"message": "没有启用的DDNS配置"}
    
    results = []
    for config in configs:
        try:
            # 检查更新间隔
            if config.last_update_at:
                time_diff = datetime.now() - config.last_update_at
                if time_diff.total_seconds() < config.update_interval:
                    results.append({
                        "config_id": config.id,
                        "name": config.name,
                        "status": "skipped",
                        "message": "未到更新时间"
                    })
                    continue
            
            # 执行更新
            response = await update_ddns_record(config.id, force=False)
            results.append({
                "config_id": config.id,
                "name": config.name,
                "status": "success" if response.success else "failed",
                "message": response.message,
                "old_ip": response.old_ip,
                "new_ip": response.new_ip
            })
            
        except Exception as e:
            results.append({
                "config_id": config.id,
                "name": config.name,
                "status": "error",
                "message": str(e)
            })
    
    success_count = sum(1 for r in results if r["status"] == "success")
    
    return {
        "message": f"批量更新完成，成功更新 {success_count} 个配置",
        "total": len(configs),
        "success": success_count,
        "results": results
    }


@router.get("/status/summary")
async def get_ddns_status_summary():
    """获取DDNS状态概览"""
    total_configs = await DDNSConfig.all().count()
    enabled_configs = await DDNSConfig.filter(enabled=True).count()
    
    # 获取最近24小时的更新统计
    yesterday = datetime.now() - timedelta(days=1)
    recent_updates = await DDNSLog.filter(
        created_at__gte=yesterday,
        status="success"
    ).count()
    
    recent_failures = await DDNSLog.filter(
        created_at__gte=yesterday,
        status="failed"
    ).count()
    
    return {
        "total_configs": total_configs,
        "enabled_configs": enabled_configs,
        "disabled_configs": total_configs - enabled_configs,
        "recent_updates": recent_updates,
        "recent_failures": recent_failures,
        "last_check": datetime.now()
    }
