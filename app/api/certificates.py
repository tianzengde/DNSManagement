"""证书管理API"""
from fastapi import APIRouter, HTTPException, Depends
from tortoise.exceptions import DoesNotExist
from typing import List
from app.models import Certificate, Domain, CertificateType, CertificateStatus
from app.schemas import (
    CertificateCreate, CertificateUpdate, CertificateResponse,
    CertificateRenewRequest, CertificateRenewResponse
)
from app.services.certificate_service import CertificateService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certificates", tags=["certificates"])

# 创建证书服务实例
certificate_service = CertificateService()


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


@router.post("/request/{domain_id}")
async def request_certificate(domain_id: int, request_data: dict = None):
    """申请SSL证书（DNS验证）"""
    try:
        # 检查域名是否存在
        domain = await Domain.get(id=domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="域名不存在")
        
        # 从请求数据中提取参数
        if request_data:
            full_domain = request_data.get('full_domain')
            subdomain = request_data.get('subdomain')
            name = request_data.get('name')
            auto_renew = request_data.get('auto_renew', True)
        else:
            full_domain = None
            subdomain = None
            name = None
            auto_renew = True
        
        # 调用证书服务申请证书
        result = await certificate_service.request_certificate(
            domain_id, 
            subdomain=subdomain,
            full_domain=full_domain,
            name=name,
            auto_renew=auto_renew
        )
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "certificate_id": result.get('certificate_id'),
                "domain": result.get('domain')
            }
        else:
            raise HTTPException(status_code=400, detail=result['message'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"申请证书失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"申请证书失败: {str(e)}")


@router.post("/renew/{certificate_id}")
async def renew_certificate_api(certificate_id: int):
    """续期证书（DNS验证）"""
    try:
        # 检查证书是否存在
        certificate = await Certificate.get(id=certificate_id)
        if not certificate:
            raise HTTPException(status_code=404, detail="证书不存在")
        
        # 调用证书服务续期证书
        result = await certificate_service.renew_certificate(certificate_id)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message'],
                "renewed_at": result.get('renewed_at')
            }
        else:
            raise HTTPException(status_code=400, detail=result['message'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"续期证书失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"续期证书失败: {str(e)}")


@router.get("/domains/{domain_id}/available")
async def get_available_subdomains(domain_id: int):
    """获取可用于申请证书的子域名"""
    try:
        # 检查域名是否存在
        domain = await Domain.get(id=domain_id)
        if not domain:
            raise HTTPException(status_code=404, detail="域名不存在")
        
        # 获取该域名的所有DNS记录
        from app.models import DNSRecord
        records = await DNSRecord.filter(domain_id=domain_id).all()
        
        # 提取子域名
        subdomains = set()
        for record in records:
            if record.name != domain.name and record.name.endswith(f".{domain.name}"):
                subdomain = record.name.replace(f".{domain.name}", "")
                if subdomain:
                    subdomains.add(subdomain)
        
        return {
            "domain": domain.name,
            "subdomains": list(subdomains),
            "main_domain_available": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可用子域名失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取可用子域名失败: {str(e)}")
