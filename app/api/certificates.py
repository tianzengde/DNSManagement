"""证书管理API"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
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
import os
import zipfile
import tempfile

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
        from datetime import timezone
        
        # 更新证书状态和续期时间
        certificate.status = CertificateStatus.VALID
        certificate.last_renewed_at = datetime.now(timezone.utc)
        certificate.not_after = datetime.now(timezone.utc) + timedelta(days=90)  # 假设续期90天
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
    from datetime import timezone
    
    # 使用UTC时间来计算截止日期
    cutoff_date = datetime.now(timezone.utc) + timedelta(days=days)
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
    from datetime import timezone
    
    # 获取当前UTC时间
    now = datetime.now(timezone.utc)
    
    if certificate.not_after:
        # 如果证书到期时间是naive datetime，转换为UTC时间
        cert_not_after = certificate.not_after
        if cert_not_after.tzinfo is None:
            cert_not_after = cert_not_after.replace(tzinfo=timezone.utc)
        
        # 如果当前时间是naive datetime，转换为UTC时间
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
            
        if cert_not_after < now:
            certificate.status = CertificateStatus.EXPIRED
        elif cert_not_after < now + timedelta(days=30):
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


@router.get("/{certificate_id}/download")
async def download_certificate(certificate_id: int):
    """下载证书文件"""
    try:
        # 获取证书信息
        certificate = await Certificate.get(id=certificate_id).prefetch_related('domain')
        if not certificate:
            raise HTTPException(status_code=404, detail="证书不存在")
        
        # 构建证书文件路径
        # 首先尝试使用证书名称，然后尝试域名名称
        cert_name = certificate.name or certificate.domain.name
        
        # 检查可能的证书文件路径
        possible_paths = [
            os.path.join("data", "certificates", "certbot_config", "live", cert_name),
            os.path.join("data", "certificates", "certbot_config", "live", certificate.domain.name),
        ]
        
        # 如果证书名称包含域名，也尝试提取子域名
        if certificate.domain.name in cert_name and cert_name != certificate.domain.name:
            # 尝试从证书名称中提取实际的域名部分
            if certificate.domain.name in cert_name:
                # 如果证书名称是 "lal.hualuo063.cn SSL证书"，提取 "lal.hualuo063.cn"
                actual_domain = cert_name.split()[0]  # 取第一个空格前的部分
                possible_paths.append(os.path.join("data", "certificates", "certbot_config", "live", actual_domain))
        
        certbot_config_path = None
        for path in possible_paths:
            if os.path.exists(os.path.join(path, "fullchain.pem")):
                certbot_config_path = path
                break
        
        if not certbot_config_path:
            raise HTTPException(status_code=404, detail="证书文件不存在")
        
        # 检查证书文件是否存在
        cert_file = os.path.join(certbot_config_path, "fullchain.pem")
        key_file = os.path.join(certbot_config_path, "privkey.pem")
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            raise HTTPException(status_code=404, detail="证书文件不存在")
        
        # 创建临时ZIP文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加证书文件
                zipf.write(cert_file, f"{cert_name}.crt")
                zipf.write(key_file, f"{cert_name}.key")
                
                # 如果有证书链文件，也添加进去
                chain_file = os.path.join(certbot_config_path, "chain.pem")
                if os.path.exists(chain_file):
                    zipf.write(chain_file, f"{cert_name}.chain.pem")
        
        # 返回ZIP文件
        # 使用安全的文件名，避免中文字符编码问题
        import urllib.parse
        import re
        
        # 清理文件名，移除特殊字符和中文字符
        clean_name = re.sub(r'[^\w\-_.]', '_', cert_name)
        clean_name = clean_name.replace("SSL证书", "ssl_cert").replace(" ", "_")
        safe_filename = f"{clean_name}_certificate.zip"
        encoded_filename = urllib.parse.quote(safe_filename)
        
        return FileResponse(
            path=temp_zip.name,
            filename=safe_filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载证书失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载证书失败: {str(e)}")
