"""域名管理API"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from tortoise.transactions import atomic
from app.models import Domain, Provider, DNSRecord
from app.schemas import DomainCreate, DomainUpdate, DomainResponse, DNSRecordCreate, DNSRecordUpdate, DNSRecordResponse

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


@router.post("/", response_model=DomainResponse)
@atomic()
async def create_domain(domain_data: DomainCreate):
    """创建域名"""
    # 检查服务商是否存在
    provider = await Provider.get_or_none(id=domain_data.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="服务商不存在")
    
    # 检查域名是否已存在
    existing_domain = await Domain.get_or_none(name=domain_data.name)
    if existing_domain:
        raise HTTPException(status_code=400, detail="域名已存在")
    
    domain = await Domain.create(**domain_data.dict())
    await domain.fetch_related('provider')
    return domain


@router.put("/{domain_id}", response_model=DomainResponse)
@atomic()
async def update_domain(domain_id: int, domain_data: DomainUpdate):
    """更新域名"""
    domain = await Domain.get_or_none(id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    await domain.update_from_dict(domain_data.dict(exclude_unset=True))
    await domain.fetch_related('provider')
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


@router.get("/{domain_id}/records", response_model=List[DNSRecordResponse])
async def get_domain_records(domain_id: int):
    """获取域名的解析记录"""
    domain = await Domain.get_or_none(id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    records = await DNSRecord.filter(domain=domain).all()
    return records


@router.post("/{domain_id}/records", response_model=DNSRecordResponse)
@atomic()
async def create_domain_record(domain_id: int, record_data: DNSRecordCreate):
    """为域名添加解析记录"""
    domain = await Domain.get_or_none(id=domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    record = await DNSRecord.create(domain=domain, **record_data.dict(exclude={'domain_id'}))
    return record


@router.put("/records/{record_id}", response_model=DNSRecordResponse)
@atomic()
async def update_domain_record(record_id: int, record_data: DNSRecordUpdate):
    """更新解析记录"""
    record = await DNSRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="解析记录不存在")
    
    await record.update_from_dict(record_data.dict(exclude_unset=True))
    return record


@router.delete("/records/{record_id}")
@atomic()
async def delete_domain_record(record_id: int):
    """删除解析记录"""
    record = await DNSRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="解析记录不存在")
    
    await record.delete()
    return {"message": "删除成功"}
