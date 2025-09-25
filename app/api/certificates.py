"""证书管理API"""
from fastapi import APIRouter, HTTPException, Depends
from tortoise.exceptions import DoesNotExist
from typing import List
from app.models import Certificate, Domain, CertificateType, CertificateStatus
from app.schemas import (
    CertificateCreate, CertificateUpdate, CertificateResponse,
    CertificateRenewRequest, CertificateRenewResponse
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("/", response_model=List[CertificateResponse])
async def get_certificates():
    """获取所有证书"""
    certificates = await Certificate.all().prefetch_related('domain', 'domain__provider')
    return certificates


@router.get("/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(certificate_id: int):
    """获取单个证书"""
    try:
        certificate = await Certificate.get(id=certificate_id).prefetch_related('domain', 'domain__provider')
        return certificate
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="证书不存在")


@router.post("/", response_model=CertificateResponse)
async def create_certificate(certificate_data: CertificateCreate):
    """创建证书"""
    # 检查域名是否存在
    try:
        domain = await Domain.get(id=certificate_data.domain_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    # 创建证书
    certificate = await Certificate.create(**certificate_data.dict())
    await certificate.fetch_related('domain', 'domain__provider')
    return certificate


@router.put("/{certificate_id}", response_model=CertificateResponse)
async def update_certificate(certificate_id: int, certificate_data: CertificateUpdate):
    """更新证书"""
    try:
        certificate = await Certificate.get(id=certificate_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="证书不存在")
    
    # 更新证书
    update_data = certificate_data.dict(exclude_unset=True)
    await certificate.update_from_dict(update_data)
    await certificate.save()
    await certificate.fetch_related('domain', 'domain__provider')
    
    return certificate


@router.delete("/{certificate_id}")
async def delete_certificate(certificate_id: int):
    """删除证书"""
    try:
        certificate = await Certificate.get(id=certificate_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="证书不存在")
    
    await certificate.delete()
    return {"message": "证书删除成功"}


@router.post("/{certificate_id}/renew", response_model=CertificateRenewResponse)
async def renew_certificate(certificate_id: int, renew_data: CertificateRenewRequest):
    """续期证书"""
    try:
        certificate = await Certificate.get(id=certificate_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="证书不存在")
    
    # 这里应该实现实际的证书续期逻辑
    # 目前只是模拟续期
    try:
        # 更新证书状态和续期时间
        certificate.status = CertificateStatus.VALID
        certificate.last_renewed_at = datetime.now()
        certificate.not_after = datetime.now() + timedelta(days=90)  # 假设续期90天
        await certificate.save()
        
        return CertificateRenewResponse(
            success=True,
            message="证书续期成功",
            renewed_at=certificate.last_renewed_at
        )
    except Exception as e:
        logger.error(f"证书续期失败: {e}")
        return CertificateRenewResponse(
            success=False,
            message=f"证书续期失败: {str(e)}"
        )


@router.get("/domain/{domain_id}", response_model=List[CertificateResponse])
async def get_certificates_by_domain(domain_id: int):
    """获取指定域名的所有证书"""
    try:
        domain = await Domain.get(id=domain_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="域名不存在")
    
    certificates = await Certificate.filter(domain_id=domain_id).prefetch_related('domain', 'domain__provider')
    return certificates


@router.get("/expiring/soon", response_model=List[CertificateResponse])
async def get_expiring_certificates(days: int = 30):
    """获取即将过期的证书"""
    cutoff_date = datetime.now() + timedelta(days=days)
    certificates = await Certificate.filter(
        not_after__lte=cutoff_date,
        status__in=[CertificateStatus.VALID, CertificateStatus.EXPIRING_SOON]
    ).prefetch_related('domain', 'domain__provider')
    
    return certificates


@router.post("/check-status/{certificate_id}")
async def check_certificate_status(certificate_id: int):
    """检查证书状态"""
    try:
        certificate = await Certificate.get(id=certificate_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="证书不存在")
    
    # 这里应该实现实际的证书状态检查逻辑
    # 目前只是模拟状态检查
    now = datetime.now()
    
    if certificate.not_after:
        if certificate.not_after < now:
            certificate.status = CertificateStatus.EXPIRED
        elif certificate.not_after < now + timedelta(days=30):
            certificate.status = CertificateStatus.EXPIRING_SOON
        else:
            certificate.status = CertificateStatus.VALID
    else:
        certificate.status = CertificateStatus.INVALID
    
    await certificate.save()
    
    return {
        "success": True,
        "message": "证书状态检查完成",
        "status": certificate.status,
        "not_after": certificate.not_after
    }
