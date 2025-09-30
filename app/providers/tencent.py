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
        # 腾讯云DNS使用DNSPod API
        self.base_url = "https://dnspod.tencentcloudapi.com"
        self.version = "2021-03-23"
        self.service = "dnspod"
    
    def _sign_request(self, action: str, params: Dict[str, Any]) -> Dict[str, str]:
        """签名请求参数 - 腾讯云API 3.0签名方法（参考ddns-go实现）"""
        algorithm = "TC3-HMAC-SHA256"
        host = f"{self.service}.tencentcloudapi.com"
        timestamp = int(datetime.now().timestamp())
        timestamp_str = str(timestamp)
        
        # 计算payload哈希
        payload = json.dumps(params, separators=(',', ':'))
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # step 1: build canonical request string
        canonical_headers = f"content-type:application/json\nhost:{host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # step 2: build string to sign
        date = datetime.utcnow().strftime('%Y-%m-%d')
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp_str}\n{credential_scope}\n{hashed_canonical_request}"
        
        # step 3: sign string
        secret_date = hmac.new(f"TC3{self.secret_key}".encode('utf-8'), date.encode('utf-8'), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, self.service.encode('utf-8'), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode('utf-8'), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # step 4: build authorization
        authorization = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        # 移除调试信息
        
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": timestamp_str,
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
                error_info = data["Response"]["Error"]
                raise Exception(f"腾讯云API错误: {error_info.get('Message', '未知错误')} (Code: {error_info.get('Code', 'N/A')})")
            
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
                error_info = data["Response"]["Error"]
                raise Exception(f"腾讯云API错误: {error_info.get('Message', '未知错误')} (Code: {error_info.get('Code', 'N/A')})")
            
            records = data.get("Response", {}).get("RecordList", [])
            result = []
            for record in records:
                try:
                    # 检查必要字段是否存在
                    if not record.get("RecordId") or not record.get("Name") or not record.get("Type"):
                        print(f"跳过无效记录: {record}")
                        continue
                    
                    result.append({
                        "id": record["RecordId"],
                        "name": record["Name"],
                        "type": record["Type"],  # 使用Type字段而不是RecordType
                        "value": record.get("Value", ""),
                        "ttl": int(record.get("TTL", 600)),
                        "priority": int(record.get("MX", 0)) if record.get("MX") else None,
                        "status": record.get("Status", "ENABLE")
                    })
                except Exception as e:
                    print(f"处理记录时出错: {record}, 错误: {e}")
                    continue
            
            return result
    
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        # 严格按照ddns-go的参数结构
        # 计算子域名部分
        record_name = record["name"]
        if record_name == domain or record_name == f"@{domain}":
            subdomain = "@"
        elif record_name.endswith(f".{domain}"):
            subdomain = record_name[:-len(f".{domain}")]
        else:
            subdomain = record_name
        
        params = {
            "Domain": domain,
            "SubDomain": subdomain,  # 子域名部分，不是完整域名
            "RecordType": record["type"],
            "RecordLine": "默认",
            "Value": record["value"],
            "TTL": record.get("ttl", 600)
        }
        
        if record.get("priority"):
            params["MX"] = record["priority"]
        
        print(f"[DEBUG] 创建记录参数: {params}")
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
            print(f"[DEBUG] 创建记录响应: {data}")
            
            if data.get("Response", {}).get("Error"):
                error_info = data["Response"]["Error"]
                print(f"[DEBUG] 创建记录错误: {error_info}")
                raise Exception(f"腾讯云API错误: {error_info.get('Message', '未知错误')} (Code: {error_info.get('Code', 'N/A')})")
            
            record_id = data.get("Response", {}).get("RecordId")
            if not record_id:
                print(f"[DEBUG] 未返回记录ID，完整响应: {data}")
                raise Exception("服务商API未返回记录ID")
            
            print(f"[DEBUG] 创建记录成功，记录ID: {record_id}")
            return str(record_id)
    
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        # 计算子域名部分
        record_name = record["name"]
        if record_name == domain or record_name == f"@{domain}":
            subdomain = "@"
        elif record_name.endswith(f".{domain}"):
            subdomain = record_name[:-len(f".{domain}")]
        else:
            subdomain = record_name
        
        params = {
            "Domain": domain,
            "RecordId": record_id,
            "SubDomain": subdomain,  # 子域名部分，不是完整域名
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
                error_info = data["Response"]["Error"]
                raise Exception(f"腾讯云API错误: {error_info.get('Message', '未知错误')} (Code: {error_info.get('Code', 'N/A')})")
            
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
                error_info = data["Response"]["Error"]
                raise Exception(f"腾讯云API错误: {error_info.get('Message', '未知错误')} (Code: {error_info.get('Code', 'N/A')})")
            
            return True
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_domains()
            return True
        except Exception as e:
            # 重新抛出异常以便上层处理
            raise e
