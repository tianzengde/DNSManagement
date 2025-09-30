"""DNS服务商集成模块"""
from .base import BaseProvider
from .huawei import HuaweiProvider
from .aliyun import AliyunProvider
from .tencent import TencentProvider
from .cloudflare import CloudflareProvider

__all__ = ['BaseProvider', 'HuaweiProvider', 'AliyunProvider', 'TencentProvider', 'CloudflareProvider']
