"""DNS服务商基础类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models import DNSRecord, RecordType


class BaseProvider(ABC):
    """DNS服务商基础抽象类"""
    
    def __init__(self, access_key: str, secret_key: str, region: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
    
    @abstractmethod
    async def get_domains(self) -> List[Dict[str, Any]]:
        """获取域名列表"""
        pass
    
    @abstractmethod
    async def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名解析记录"""
        pass
    
    @abstractmethod
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        pass
    
    @abstractmethod
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        pass
    
    @abstractmethod
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """删除解析记录"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass
    
    def _convert_record_type(self, record_type: str) -> RecordType:
        """转换记录类型"""
        type_mapping = {
            'A': RecordType.A,
            'AAAA': RecordType.AAAA,
            'CNAME': RecordType.CNAME,
            'MX': RecordType.MX,
            'TXT': RecordType.TXT,
            'NS': RecordType.NS,
        }
        return type_mapping.get(record_type.upper(), RecordType.A)
