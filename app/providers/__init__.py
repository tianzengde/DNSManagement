"""DNS服务商集成模块"""
from .base import BaseProvider
from .huawei import HuaweiProvider
from .aliyun import AliyunProvider

__all__ = ['BaseProvider', 'HuaweiProvider', 'AliyunProvider']
