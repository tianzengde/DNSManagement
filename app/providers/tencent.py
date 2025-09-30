"""腾讯云DNS服务商集成"""
import httpx
import hashlib
import hmac
import base64
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode, quote
from .base import BaseProvider


class TencentProvider(BaseProvider):
    """腾讯云DNS服务商"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = ""):
        super().__init__(access_key, secret_key, region)
        # 腾讯云DNS是全局服务，不需要区域参数
        self.base_url = "https://cns.tencentcloudapi.com"
        self.version = "2021-03-23"
        self.service = "cns"
    
    def _sign_request(self, action: str, params: Dict[str, Any]) -> Dict[str, str]:
        """签名请求参数 - 腾讯云API 3.0签名方法"""
        # 添加公共参数
        timestamp = int(datetime.now().timestamp())
        params.update({
            "Action": action,
            "Version": self.version,
            "Region": self.region or "ap-beijing",
            "Timestamp": timestamp,
            "Nonce": timestamp,
            "SecretId": self.access_key,
        })
        
        # 排序参数
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # 创建签名字符串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{self.base_url.replace('https://', '')}\n"
        signed_headers = "content-type;host"
        
        # 计算payload哈希
        payload = json.dumps(params, separators=(',', ':'))
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # 创建规范请求
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # 创建待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        date = datetime.utcnow().strftime('%Y-%m-%d')
        credential_scope = f"{date}/{self.service}/tc3_request"
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # 计算签名
        secret_date = hmac.new(f"TC3{self.secret_key}".encode('utf-8'), date.encode('utf-8'), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, self.service.encode('utf-8'), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode('utf-8'), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # 构建Authorization头
        authorization = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.base_url.replace('https://', ''),
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
        }
    
    async def get_domains(self) -> List[Dict[str, Any]]:
        """获取域名列表"""
        params = {
            "Limit": 100,
            "Offset": 0
        }
        
        headers = self._sign_request("DescribeDomainList", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response", {}).get("Error"):
                raise Exception(f"腾讯云API错误: {data['Response']['Error']['Message']}")
            
            domains = data.get("Response", {}).get("DomainList", [])
            return [
                {
                    "id": domain["DomainId"],
                    "name": domain["Name"],
                    "status": domain.get("Status", "ENABLE"),
                    "ttl": domain.get("TTL", 600)
                }
                for domain in domains
            ]
    
    async def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名解析记录"""
        params = {
            "Domain": domain,
            "Limit": 100,
            "Offset": 0
        }
        
        headers = self._sign_request("DescribeRecordList", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response", {}).get("Error"):
                raise Exception(f"腾讯云API错误: {data['Response']['Error']['Message']}")
            
            records = data.get("Response", {}).get("RecordList", [])
            return [
                {
                    "id": record["RecordId"],
                    "name": record["Name"],
                    "type": record["Type"],
                    "value": record["Value"],
                    "ttl": int(record.get("TTL", 600)),
                    "priority": int(record.get("MX", 0)) if record.get("MX") else None,
                    "status": record.get("Status", "ENABLE")
                }
                for record in records
            ]
    
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        params = {
            "Domain": domain,
            "SubDomain": record["name"],
            "RecordType": record["type"],
            "RecordLine": "默认",
            "Value": record["value"],
            "TTL": record.get("ttl", 600)
        }
        
        if record.get("priority"):
            params["MX"] = record["priority"]
        
        headers = self._sign_request("CreateRecord", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("Response", {}).get("Error"):
                raise Exception(f"腾讯云API错误: {data['Response']['Error']['Message']}")
            
            record_id = data.get("Response", {}).get("RecordId")
            if not record_id:
                raise Exception("服务商API未返回记录ID")
            
            return str(record_id)
    
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        params = {
            "Domain": domain,
            "RecordId": record_id,
            "SubDomain": record["name"],
            "RecordType": record["type"],
            "RecordLine": "默认",
            "Value": record["value"],
            "TTL": record.get("ttl", 600)
        }
        
        if record.get("priority"):
            params["MX"] = record["priority"]
        
        headers = self._sign_request("ModifyRecord", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("Response", {}).get("Error"):
                raise Exception(f"腾讯云API错误: {data['Response']['Error']['Message']}")
            
            return True
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """删除解析记录"""
        params = {
            "Domain": domain,
            "RecordId": record_id
        }
        
        headers = self._sign_request("DeleteRecord", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("Response", {}).get("Error"):
                raise Exception(f"腾讯云API错误: {data['Response']['Error']['Message']}")
            
            return True
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_domains()
            return True
        except Exception as e:
            # 重新抛出异常以便上层处理
            raise e
