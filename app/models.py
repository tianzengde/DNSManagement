"""数据模型定义"""
from tortoise.models import Model
from tortoise import fields
from datetime import datetime
from enum import IntEnum


class ProviderType(IntEnum):
    """DNS服务商类型"""
    HUAWEI = 1
    ALIYUN = 2


class RecordType(IntEnum):
    """DNS记录类型"""
    A = 1
    AAAA = 2
    CNAME = 3
    MX = 4
    TXT = 5
    NS = 6


class CertificateType(IntEnum):
    """证书类型"""
    LETSENCRYPT = 1
    CUSTOM = 2
    SELF_SIGNED = 3


class CertificateStatus(IntEnum):
    """证书状态"""
    VALID = 1
    EXPIRED = 2
    EXPIRING_SOON = 3
    INVALID = 4
    PENDING = 5


class Provider(Model):
    """DNS服务商模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="服务商名称")
    type = fields.IntEnumField(ProviderType, description="服务商类型")
    access_key = fields.CharField(max_length=200, description="访问密钥")
    secret_key = fields.CharField(max_length=200, description="秘密密钥")
    region = fields.CharField(max_length=50, default="", description="区域（可选）")
    enabled = fields.BooleanField(default=True, description="是否启用")
    status = fields.CharField(max_length=20, default="unknown", description="连接状态")
    last_test_at = fields.DatetimeField(null=True, description="最后测试时间")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "providers"


class Domain(Model):
    """域名模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True, description="域名")
    provider = fields.ForeignKeyField('models.Provider', related_name='domains', description="所属服务商")
    enabled = fields.BooleanField(default=True, description="是否启用")
    auto_update = fields.BooleanField(default=False, description="是否自动更新")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "domains"


class DNSRecord(Model):
    """DNS记录模型"""
    id = fields.IntField(pk=True)
    domain = fields.ForeignKeyField('models.Domain', related_name='records', description="所属域名")
    name = fields.CharField(max_length=255, description="记录名称")
    type = fields.IntEnumField(RecordType, description="记录类型")
    value = fields.CharField(max_length=500, description="记录值")
    ttl = fields.IntField(default=600, description="TTL值")
    priority = fields.IntField(null=True, description="优先级")
    enabled = fields.BooleanField(default=True, description="是否启用")
    external_id = fields.CharField(max_length=255, null=True, description="服务商记录ID")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "dns_records"


class Certificate(Model):
    """SSL证书模型"""
    id = fields.IntField(pk=True)
    domain = fields.ForeignKeyField('models.Domain', related_name='certificates', description="所属域名")
    name = fields.CharField(max_length=255, description="证书名称")
    type = fields.IntEnumField(CertificateType, description="证书类型")
    status = fields.IntEnumField(CertificateStatus, default=CertificateStatus.PENDING, description="证书状态")
    certificate_file = fields.TextField(null=True, description="证书文件内容")
    private_key_file = fields.TextField(null=True, description="私钥文件内容")
    ca_bundle_file = fields.TextField(null=True, description="CA证书链文件内容")
    issuer = fields.CharField(max_length=255, null=True, description="颁发机构")
    subject = fields.CharField(max_length=255, null=True, description="证书主题")
    serial_number = fields.CharField(max_length=100, null=True, description="序列号")
    not_before = fields.DatetimeField(null=True, description="生效时间")
    not_after = fields.DatetimeField(null=True, description="过期时间")
    auto_renew = fields.BooleanField(default=True, description="是否自动续期")
    renewal_days = fields.IntField(default=30, description="提前续期天数")
    last_renewed_at = fields.DatetimeField(null=True, description="最后续期时间")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "certificates"


class TaskLog(Model):
    """任务日志模型"""
    id = fields.IntField(pk=True)
    domain = fields.ForeignKeyField('models.Domain', related_name='task_logs', description="相关域名")
    action = fields.CharField(max_length=50, description="操作类型")
    status = fields.CharField(max_length=20, description="执行状态")
    message = fields.TextField(description="日志消息")
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "task_logs"
