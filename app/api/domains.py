"""域名管理API"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from tortoise.transactions import atomic
from app.models import Domain, Provider, DNSRecord
from app.schemas import DomainResponse, DNSRecordCreate, DNSRecordUpdate, DNSRecordResponse

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("/", response_model=List[DomainResponse])
async def get_domains(provider_id: Optional[int] = Query(None, description="按服务商ID筛选")):
    """获取域名列表"""
    query = Domain.all().prefetch_related('provider', 'records')
    
    if provider_id:
        query = query.filter(provider_id=provider_id)
    
    domains = await query
    return domains


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(domain_id: int):
    """获取单个域名"""
    domain = await Domain.get_or_none(id=domain_id).prefetch_related('provider')
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    return domain






@router.delete("/{domain_id}")
@atomic()
async def delete_domain(domain_id: int):
    """删除域名"""
    domain = await Domain.get_or_none(id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 删除相关记录
    await DNSRecord.filter(domain=domain).delete()
    await domain.delete()
    return {"message": "删除成功"}


@router.get("/{domain_id}/records")
async def get_domain_records(
    domain_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(5, ge=1, le=100, description="每页记录数"),
    search: Optional[str] = Query(None, description="按记录名称搜索")
):
    """获取域名的解析记录（分页+搜索）"""
    domain = await Domain.get_or_none(id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 构建查询条件
    query = DNSRecord.filter(domain=domain)
    
    # 如果有搜索条件，添加名称模糊匹配
    if search and search.strip():
        query = query.filter(name__icontains=search.strip())
    
    # 计算偏移量
    offset = (page - 1) * page_size
    
    # 获取总记录数
    total = await query.count()
    
    # 获取分页记录
    records = await query.offset(offset).limit(page_size).all()
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "records": records,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "search": search
    }


@router.post("/{domain_id}/records", response_model=DNSRecordResponse)
@atomic()
async def create_domain_record(domain_id: int, record_data: DNSRecordCreate):
    """为域名添加解析记录"""
    domain = await Domain.get_or_none(id=domain_id).prefetch_related('provider')
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 获取服务商实例
    provider = None
    if domain.provider.type == 1:  # 华为云
        from app.providers.huawei import HuaweiProvider
        provider = HuaweiProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-north-4"
        )
    elif domain.provider.type == 2:  # 阿里云
        from app.providers.aliyun import AliyunProvider
        provider = AliyunProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-hangzhou"
        )
    elif domain.provider.type == 3:  # 腾讯云
        from app.providers.tencent import TencentProvider
        provider = TencentProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "ap-beijing"
        )
    elif domain.provider.type == 4:  # Cloudflare
        from app.providers.cloudflare import CloudflareProvider
        provider = CloudflareProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or ""
        )
    
    if not provider:
        raise HTTPException(status_code=400, detail="不支持的服务商类型")
    
    # 准备记录数据
    record_dict = record_data.dict(exclude={'domain_id'})
    
    # 转换记录类型为字符串
    type_mapping = {
        1: 'A',
        2: 'AAAA', 
        3: 'CNAME',
        4: 'MX',
        5: 'TXT',
        6: 'NS'
    }
    record_type = type_mapping.get(record_dict['type'], 'A')
    
    # 构建API调用参数
    api_record = {
        "name": record_dict['name'],
        "type": record_type,
        "value": record_dict['value'],
        "ttl": record_dict['ttl']
    }
    
    try:
        # 先调用官方API添加记录
        external_id = await provider.add_record(domain.name, api_record)
        if not external_id:
            raise HTTPException(status_code=500, detail="调用服务商API失败")
        
        # API调用成功，保存到本地数据库
        record_dict['external_id'] = external_id
        record = await DNSRecord.create(domain=domain, **record_dict)
        return record
        
    except Exception as e:
        # API调用失败，抛出错误（事务会自动回滚）
        raise HTTPException(status_code=500, detail=f"添加解析记录失败: {str(e)}")


@router.put("/records/{record_id}", response_model=DNSRecordResponse)
@atomic()
async def update_domain_record(record_id: int, record_data: DNSRecordUpdate):
    """更新解析记录"""
    record = await DNSRecord.get_or_none(id=record_id).prefetch_related('domain__provider')
    if not record:
        raise HTTPException(status_code=404, detail="解析记录不存在")
    
    domain = record.domain
    provider_instance = None
    
    # 获取服务商实例
    if domain.provider.type == 1:  # 华为云
        from app.providers.huawei import HuaweiProvider
        provider_instance = HuaweiProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-north-4"
        )
    elif domain.provider.type == 2:  # 阿里云
        from app.providers.aliyun import AliyunProvider
        provider_instance = AliyunProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-hangzhou"
        )
    elif domain.provider.type == 3:  # 腾讯云
        from app.providers.tencent import TencentProvider
        provider_instance = TencentProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "ap-beijing"
        )
    elif domain.provider.type == 4:  # Cloudflare
        from app.providers.cloudflare import CloudflareProvider
        provider_instance = CloudflareProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or ""
        )
    
    if not provider_instance:
        raise HTTPException(status_code=400, detail="不支持的服务商类型")
    
    # 保存原始数据用于回滚
    original_data = {
        'name': record.name,
        'type': record.type,
        'value': record.value,
        'ttl': record.ttl,
        'enabled': record.enabled
    }
    
    # 准备更新数据
    update_dict = record_data.dict(exclude_unset=True)
    
    # 转换记录类型为字符串
    type_mapping = {
        1: 'A',
        2: 'AAAA', 
        3: 'CNAME',
        4: 'MX',
        5: 'TXT',
        6: 'NS'
    }
    
    # 构建API调用参数
    record_type = type_mapping.get(update_dict.get('type', record.type), 'A')
    record_value = update_dict.get('value', record.value)
    
    # 验证A记录的IP地址格式
    if record_type == 'A':
        import re
        ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(ip_pattern, record_value)
        if not match:
            raise HTTPException(status_code=400, detail="A记录的IP地址格式不正确")
        
        # 检查每个段是否在0-255范围内
        for segment in match.groups():
            if int(segment) > 255:
                raise HTTPException(status_code=400, detail=f"IP地址段 {segment} 超出范围(0-255)")
    
    api_record = {
        "name": update_dict.get('name', record.name),
        "type": record_type,
        "value": record_value,
        "ttl": update_dict.get('ttl', record.ttl)
    }
    
    try:
        # 先调用官方API更新记录
        # 注意：这里需要record的外部ID，我们需要从同步时保存的external_id获取
        external_id = getattr(record, 'external_id', None)
        if not external_id:
            raise HTTPException(status_code=400, detail="记录缺少外部ID，无法更新")
        
        success = await provider_instance.update_record(domain.name, external_id, api_record)
        if not success:
            raise HTTPException(status_code=500, detail="调用服务商API失败")
        
        # API调用成功，更新本地数据库
        # 直接更新字段，避免update_from_dict的问题
        if 'name' in update_dict:
            record.name = update_dict['name']
        if 'type' in update_dict:
            record.type = update_dict['type']
        if 'value' in update_dict:
            record.value = update_dict['value']
        if 'ttl' in update_dict:
            record.ttl = update_dict['ttl']
        if 'priority' in update_dict:
            record.priority = update_dict['priority']
        if 'enabled' in update_dict:
            record.enabled = update_dict['enabled']
        
        await record.save()
        return record
        
    except Exception as e:
        # API调用失败，抛出错误（事务会自动回滚）
        raise HTTPException(status_code=500, detail=f"更新解析记录失败: {str(e)}")


@router.delete("/records/{record_id}")
@atomic()
async def delete_domain_record(record_id: int):
    """删除解析记录"""
    record = await DNSRecord.get_or_none(id=record_id).prefetch_related('domain__provider')
    if not record:
        raise HTTPException(status_code=404, detail="解析记录不存在")
    
    domain = record.domain
    provider_instance = None
    
    # 获取服务商实例
    if domain.provider.type == 1:  # 华为云
        from app.providers.huawei import HuaweiProvider
        provider_instance = HuaweiProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-north-4"
        )
    elif domain.provider.type == 2:  # 阿里云
        from app.providers.aliyun import AliyunProvider
        provider_instance = AliyunProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "cn-hangzhou"
        )
    elif domain.provider.type == 3:  # 腾讯云
        from app.providers.tencent import TencentProvider
        provider_instance = TencentProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or "ap-beijing"
        )
    elif domain.provider.type == 4:  # Cloudflare
        from app.providers.cloudflare import CloudflareProvider
        provider_instance = CloudflareProvider(
            access_key=domain.provider.access_key,
            secret_key=domain.provider.secret_key,
            region=domain.provider.region or ""
        )
    
    if not provider_instance:
        raise HTTPException(status_code=400, detail="不支持的服务商类型")
    
    try:
        # 先调用官方API删除记录
        external_id = getattr(record, 'external_id', None)
        if not external_id:
            raise HTTPException(status_code=400, detail="记录缺少外部ID，无法删除")
        
        success = await provider_instance.delete_record(domain.name, external_id)
        if not success:
            raise HTTPException(status_code=500, detail="调用服务商API失败")
        
        # API调用成功，删除本地数据库记录
        await record.delete()
        return {"message": "删除成功"}
        
    except Exception as e:
        # API调用失败，抛出错误（事务会自动回滚）
        raise HTTPException(status_code=500, detail=f"删除解析记录失败: {str(e)}")
