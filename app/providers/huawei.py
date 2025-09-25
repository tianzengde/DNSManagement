"""华为云DNS服务商集成"""
import httpx
import hashlib
import hmac
import base64
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode, quote
from .base import BaseProvider


class HuaweiProvider(BaseProvider):
    """华为云DNS服务商"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = ""):
        super().__init__(access_key, secret_key, region)
        # 如果没有指定区域，使用默认区域
        if not region:
            region = "cn-north-4"
        self.region = region
        self.base_url = "https://dns.myhuaweicloud.com"
        self.service = "dns"
        self.token = None
    
    def _escape_uri(self, uri: str) -> str:
        """URL编码 - 参考ddns-go的escape函数"""
        # 简化版本，只处理基本字符
        return quote(uri, safe='/-._~')
    
    def _canonical_uri(self, uri: str) -> str:
        """规范URI - 参考ddns-go的CanonicalURI"""
        patterns = uri.split('/')
        escaped_patterns = [self._escape_uri(p) for p in patterns]
        canonical_uri = '/'.join(escaped_patterns)
        if not canonical_uri.endswith('/'):
            canonical_uri += '/'
        return canonical_uri
    
    def _canonical_query_string(self, query_params: Dict[str, str]) -> str:
        """规范查询字符串"""
        if not query_params:
            return ""
        
        # 排序并编码参数
        sorted_params = []
        for key in sorted(query_params.keys()):
            value = query_params[key]
            escaped_key = self._escape_uri(key)
            escaped_value = self._escape_uri(str(value))
            sorted_params.append(f"{escaped_key}={escaped_value}")
        
        return '&'.join(sorted_params)
    
    def _canonical_headers(self, headers: Dict[str, str], signed_headers: list, host: str) -> str:
        """规范请求头"""
        canonical_headers = []
        for header in signed_headers:
            if header == 'host':
                value = host
            else:
                # 将header key转换为小写来匹配
                original_key = None
                for k in headers.keys():
                    if k.lower() == header:
                        original_key = k
                        break
                value = headers.get(original_key, '') if original_key else ''
            canonical_headers.append(f"{header}:{value.strip()}")
        return '\n'.join(canonical_headers) + '\n'
    
    def _hex_encode_sha256_hash(self, body: str) -> str:
        """计算请求体的SHA256哈希值"""
        return hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    def _sign_request(self, method: str, uri: str, query_params: Dict[str, str], 
                     headers: Dict[str, str], body: str = "") -> Dict[str, str]:
        """签名请求 - 完全按照ddns-go的签名方式"""
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        # 设置X-Sdk-Date头
        headers['X-Sdk-Date'] = timestamp
        
        # 添加host头到签名头列表中
        host = 'dns.myhuaweicloud.com'
        all_headers = dict(headers)
        all_headers['host'] = host
        
        # 获取签名头列表（按字母顺序排序）
        signed_headers = sorted([k.lower() for k in all_headers.keys()])
        
        # 计算payload hash
        payload_hash = self._hex_encode_sha256_hash(body)
        
        # 构建规范请求
        canonical_uri = self._canonical_uri(uri)
        canonical_query_string = self._canonical_query_string(query_params)
        canonical_headers = self._canonical_headers(headers, signed_headers, host)
        signed_headers_str = ';'.join(signed_headers)
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n{signed_headers_str}\n{payload_hash}"
        
        # 构建待签名字符串
        canonical_request_hash = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = f"SDK-HMAC-SHA256\n{timestamp}\n{canonical_request_hash}"
        
        # 计算签名 - 直接使用secret_key
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # 设置Authorization头
        headers['Authorization'] = f"SDK-HMAC-SHA256 Access={self.access_key}, SignedHeaders={signed_headers_str}, Signature={signature}"
        
        return headers
    
    async def get_domains(self) -> List[Dict[str, Any]]:
        """获取域名列表"""
        uri = "/v2/zones"
        query_params = {"limit": 100}
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        headers = self._sign_request("GET", uri, query_params, headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{uri}",
                params=query_params,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "id": zone["id"],
                    "name": zone["name"],
                    "status": zone.get("status", "ACTIVE"),
                    "ttl": zone.get("ttl", 300)
                }
                for zone in data.get("zones", [])
            ]
    
    async def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名解析记录"""
        # 首先获取域名ID
        zones = await self.get_domains()
        domain_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                domain_id = zone["id"]
                break
        
        if not domain_id:
            return []
        
        # 使用域名ID查询该域名下的所有记录
        uri = f"/v2/zones/{domain_id}/recordsets"
        query_params = {
            "limit": 100
        }
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        headers = self._sign_request("GET", uri, query_params, headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{uri}",
                params=query_params,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "records": record.get("records", []),
                    "ttl": record.get("ttl", 300),
                    "status": record.get("status", "ACTIVE"),
                    "zone_id": record.get("zone_id", "")
                }
                for record in data.get("recordsets", [])
            ]
    
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        # 首先获取域名ID
        zones = await self.get_domains()
        domain_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                domain_id = zone["id"]
                break
        
        if not domain_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        uri = f"/v2/zones/{domain_id}/recordsets"
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        body = {
            "name": record["name"],
            "type": record["type"],
            "records": [record["value"]],
            "ttl": record.get("ttl", 300)
        }
        
        if record.get("priority"):
            body["priority"] = record["priority"]
        
        body_str = json.dumps(body)
        headers = self._sign_request("POST", uri, {}, headers, body_str)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{uri}",
                data=body_str,
                headers=headers,
                timeout=60
            )
            if response.status_code not in [201, 202]:
                error_detail = response.text
                raise Exception(f"华为云API返回错误 {response.status_code}: {error_detail}")
            
            # 解析响应获取记录ID
            result = response.json()
            record_id = result.get("id")
            if not record_id:
                raise Exception("服务商API未返回记录ID")
            
            return str(record_id)
    
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        # 首先获取域名ID
        zones = await self.get_domains()
        domain_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                domain_id = zone["id"]
                break
        
        if not domain_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        uri = f"/v2/zones/{domain_id}/recordsets/{record_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        body = {
            "name": record["name"],
            "type": record["type"],
            "records": [record["value"]],
            "ttl": record.get("ttl", 300)
        }
        
        if record.get("priority"):
            body["priority"] = record["priority"]
        
        body_str = json.dumps(body)
        headers = self._sign_request("PUT", uri, {}, headers, body_str)
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}{uri}",
                data=body_str,
                headers=headers,
                timeout=60
            )
            if response.status_code not in [200, 202]:
                error_detail = response.text
                raise Exception(f"华为云API返回错误 {response.status_code}: {error_detail}")
            return True
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """删除解析记录"""
        # 首先获取域名ID
        zones = await self.get_domains()
        domain_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                domain_id = zone["id"]
                break
        
        if not domain_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        uri = f"/v2/zones/{domain_id}/recordsets/{record_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        }
        
        headers = self._sign_request("DELETE", uri, {}, headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{uri}",
                headers=headers,
                timeout=60
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
