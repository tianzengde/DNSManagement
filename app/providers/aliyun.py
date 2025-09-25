"""阿里云DNS服务商集成"""
import httpx
import hashlib
import hmac
import base64
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode, quote
from .base import BaseProvider


class AliyunProvider(BaseProvider):
    """阿里云DNS服务商"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = ""):
        super().__init__(access_key, secret_key, region)
        # 阿里云DNS是全局服务，不需要区域参数
        self.base_url = "https://alidns.aliyuncs.com"
        self.version = "2015-01-09"
    
    def _sign_request(self, params: Dict[str, str]) -> str:
        """签名请求参数"""
        # 添加公共参数
        params.update({
            "Format": "JSON",
            "Version": self.version,
            "AccessKeyId": self.access_key,
            "SignatureMethod": "HMAC-SHA1",
            "Timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "SignatureVersion": "1.0",
            "SignatureNonce": str(int(datetime.now().timestamp() * 1000))
        })
        
        # 排序参数
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # 创建签名字符串
        string_to_sign = f"GET&%2F&{quote(query_string, safe='')}"
        
        # 计算签名
        signature = base64.b64encode(
            hmac.new(
                f"{self.secret_key}&".encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        params["Signature"] = signature
        return urlencode(params)
    
    async def get_domains(self) -> List[Dict[str, Any]]:
        """获取域名列表"""
        params = {
            "Action": "DescribeDomains",
            "PageNumber": "1",
            "PageSize": "100"
        }
        
        query_string = self._sign_request(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}?{query_string}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "id": domain["DomainId"],
                    "name": domain["DomainName"],
                    "status": domain.get("DomainStatus", "ENABLE"),
                    "ttl": domain.get("Ttl", 600)
                }
                for domain in data.get("Domains", {}).get("Domain", [])
            ]
    
    async def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名解析记录"""
        params = {
            "Action": "DescribeDomainRecords",
            "DomainName": domain,
            "PageNumber": "1",
            "PageSize": "100"
        }
        
        query_string = self._sign_request(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}?{query_string}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "id": record["RecordId"],
                    "name": record["RR"],
                    "type": record["Type"],
                    "value": record["Value"],
                    "ttl": int(record.get("TTL", 600)),
                    "priority": int(record.get("Priority", 0)) if record.get("Priority") else None,
                    "status": record.get("Status", "ENABLE")
                }
                for record in data.get("DomainRecords", {}).get("Record", [])
            ]
    
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        params = {
            "Action": "AddDomainRecord",
            "DomainName": domain,
            "RR": record["name"],
            "Type": record["type"],
            "Value": record["value"],
            "TTL": str(record.get("ttl", 600))
        }
        
        if record.get("priority"):
            params["Priority"] = str(record["priority"])
        
        query_string = self._sign_request(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}?{query_string}",
                timeout=30
            )
            response.raise_for_status()
            
            # 解析响应获取记录ID
            result = response.json()
            record_id = result.get("RecordId")
            if not record_id:
                raise Exception("服务商API未返回记录ID")
            
            return str(record_id)
    
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        params = {
            "Action": "UpdateDomainRecord",
            "RecordId": record_id,
            "RR": record["name"],
            "Type": record["type"],
            "Value": record["value"],
            "TTL": str(record.get("ttl", 600))
        }
        
        if record.get("priority"):
            params["Priority"] = str(record["priority"])
        
        query_string = self._sign_request(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}?{query_string}",
                timeout=30
            )
            response.raise_for_status()
            return True
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """删除解析记录"""
        params = {
            "Action": "DeleteDomainRecord",
            "RecordId": record_id
        }
        
        query_string = self._sign_request(params)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}?{query_string}",
                timeout=30
            )
            response.raise_for_status()
            return True
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_domains()
            return True
        except Exception as e:
            # 重新抛出异常以便上层处理
            raise e
