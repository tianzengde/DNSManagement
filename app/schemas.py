"""Pydantic模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models import ProviderType, RecordType, CertificateType, CertificateStatus


class ProviderBase(BaseModel):
    """服务商基础模型"""
    name: str = Field(..., description="服务商名称")
    type: ProviderType = Field(..., description="服务商类型")
    access_key: str = Field(..., description="访问密钥")
    secret_key: str = Field(..., description="秘密密钥")
    region: str = Field("", description="区域（可选）")
    enabled: bool = Field(True, description="是否启用")
    status: str = Field("unknown", description="连接状态")
    last_test_at: Optional[datetime] = Field(None, description="最后测试时间")


class ProviderCreate(ProviderBase):
    """创建服务商模型"""
    pass


class ProviderUpdate(BaseModel):
    """更新服务商模型"""
    name: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None
    enabled: Optional[bool] = None


class ProviderResponse(ProviderBase):
    """服务商响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DomainBase(BaseModel):
    """域名基础模型"""
    name: str = Field(..., description="域名")
    provider_id: int = Field(..., description="服务商ID")
    enabled: bool = Field(True, description="是否启用")
    auto_update: bool = Field(False, description="是否自动更新")






class DomainResponse(DomainBase):
    """域名响应模型"""
    id: int
    provider: ProviderResponse
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DNSRecordBase(BaseModel):
    """DNS记录基础模型"""
    name: str = Field(..., description="记录名称")
    type: RecordType = Field(..., description="记录类型")
    value: str = Field(..., description="记录值")
    ttl: int = Field(600, description="TTL值")
    priority: Optional[int] = Field(None, description="优先级")
    enabled: bool = Field(True, description="是否启用")


class DNSRecordCreate(DNSRecordBase):
    """创建DNS记录模型"""
    domain_id: int = Field(..., description="域名ID")


class DNSRecordUpdate(BaseModel):
    """更新DNS记录模型"""
    name: Optional[str] = None
    type: Optional[RecordType] = None
    value: Optional[str] = None
    ttl: Optional[int] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class DNSRecordResponse(DNSRecordBase):
    """DNS记录响应模型"""
    id: int
    domain_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskLogResponse(BaseModel):
    """任务日志响应模型"""
    id: int
    domain_id: int
    action: str
    status: str
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    """同步请求模型"""
    domain_id: int = Field(..., description="域名ID")
    force: bool = Field(False, description="是否强制同步")


class SyncResponse(BaseModel):
    """同步响应模型"""
    success: bool
    message: str
    records_added: int = 0
    records_updated: int = 0
    records_deleted: int = 0


class CertificateBase(BaseModel):
    """证书基础模型"""
    name: str = Field(..., description="证书名称")
    domain_id: int = Field(..., description="所属域名ID")
    type: CertificateType = Field(..., description="证书类型")
    status: CertificateStatus = Field(CertificateStatus.PENDING, description="证书状态")
    certificate_file: Optional[str] = Field(None, description="证书文件内容")
    private_key_file: Optional[str] = Field(None, description="私钥文件内容")
    ca_bundle_file: Optional[str] = Field(None, description="CA证书链文件内容")
    issuer: Optional[str] = Field(None, description="颁发机构")
    subject: Optional[str] = Field(None, description="证书主题")
    serial_number: Optional[str] = Field(None, description="序列号")
    not_before: Optional[datetime] = Field(None, description="生效时间")
    not_after: Optional[datetime] = Field(None, description="过期时间")
    auto_renew: bool = Field(True, description="是否自动续期")
    renewal_days: int = Field(30, description="提前续期天数")


class CertificateCreate(CertificateBase):
    """创建证书模型"""
    pass


class CertificateUpdate(BaseModel):
    """更新证书模型"""
    name: Optional[str] = None
    type: Optional[CertificateType] = None
    certificate_file: Optional[str] = None
    private_key_file: Optional[str] = None
    ca_bundle_file: Optional[str] = None
    auto_renew: Optional[bool] = None
    renewal_days: Optional[int] = None


class CertificateResponse(CertificateBase):
    """证书响应模型"""
    id: int
    domain: DomainResponse
    last_renewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CertificateRenewRequest(BaseModel):
    """证书续期请求模型"""
    certificate_id: int = Field(..., description="证书ID")
    force: bool = Field(False, description="是否强制续期")


class CertificateRenewResponse(BaseModel):
    """证书续期响应模型"""
    success: bool
    message: str
    renewed_at: Optional[datetime] = None
