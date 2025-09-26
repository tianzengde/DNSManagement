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
    pass


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


# 用户认证相关模型
class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserPasswordChange(BaseModel):
    """用户密码修改模型"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DDNSConfigBase(BaseModel):
    """DDNS配置基础模型"""
    name: str = Field(..., description="DDNS配置名称")
    domain_id: int = Field(..., description="关联域名ID")
    subdomain: str = Field(..., description="子域名")
    record_type: RecordType = Field(RecordType.A, description="记录类型")
    enabled: bool = Field(True, description="是否启用")
    update_interval: int = Field(300, description="更新间隔(秒)")
    update_method: str = Field("auto", description="更新方式")


class DDNSConfigCreate(DDNSConfigBase):
    """创建DDNS配置模型"""
    pass


class DDNSConfigUpdate(BaseModel):
    """更新DDNS配置模型"""
    name: Optional[str] = None
    subdomain: Optional[str] = None
    record_type: Optional[RecordType] = None
    enabled: Optional[bool] = None
    update_interval: Optional[int] = None
    update_method: Optional[str] = None


class DDNSConfigResponse(DDNSConfigBase):
    """DDNS配置响应模型"""
    id: str
    domain: DomainResponse
    last_update_at: Optional[datetime] = None
    last_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DDNSLogResponse(BaseModel):
    """DDNS日志响应模型"""
    id: int
    ddns_config_id: str
    old_ip: Optional[str] = None
    new_ip: str
    status: str
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DDNSUpdateRequest(BaseModel):
    """DDNS更新请求模型"""
    ddns_config_id: int = Field(..., description="DDNS配置ID")
    force: bool = Field(False, description="是否强制更新")


class DDNSUpdateResponse(BaseModel):
    """DDNS更新响应模型"""
    success: bool
    message: str
    old_ip: Optional[str] = None
    new_ip: Optional[str] = None
    updated_at: Optional[datetime] = None


class DashboardStats(BaseModel):
    """首页统计模型"""
    total_providers: int = Field(..., description="总服务商数")
    enabled_providers: int = Field(..., description="启用的服务商数")
    total_domains: int = Field(..., description="总域名数")
    total_certificates: int = Field(..., description="总证书数")
    valid_certificates: int = Field(..., description="有效证书数")
    expiring_certificates: int = Field(..., description="即将过期证书数")
    total_ddns_configs: int = Field(..., description="总DDNS配置数")
    active_ddns_configs: int = Field(..., description="活跃DDNS配置数")