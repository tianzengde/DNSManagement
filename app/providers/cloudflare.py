"""Cloudflare DNS服务商集成"""
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any
from .base import BaseProvider


class CloudflareProvider(BaseProvider):
    """Cloudflare DNS服务商"""
    
    def __init__(self, access_key: str, secret_key: str, region: str = ""):
        super().__init__(access_key, secret_key, region)
        # Cloudflare使用API Token，access_key是token，secret_key是email（用于某些API）
        self.api_token = access_key
        self.email = secret_key
        self.base_url = "https://api.cloudflare.com/client/v4"
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    async def get_domains(self) -> List[Dict[str, Any]]:
        """获取域名列表（Zones）"""
        headers = self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/zones",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                messages = data.get("messages", [])
                errors = data.get("errors", [])
                if messages:
                    error_msg = ", ".join(messages)
                elif errors:
                    error_msg = ", ".join([error.get("message", "未知错误") for error in errors])
                else:
                    error_msg = "未知错误"
                raise Exception(f"Cloudflare API错误: {error_msg}")
            
            zones = data.get("result", [])
            return [
                {
                    "id": zone["id"],
                    "name": zone["name"],
                    "status": zone.get("status", "active"),
                    "ttl": zone.get("plan", {}).get("legacy_id", 1)  # 使用plan作为TTL参考
                }
                for zone in zones
            ]
    
    async def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名解析记录"""
        # 首先获取zone_id
        zones = await self.get_domains()
        zone_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                zone_id = zone["id"]
                break
        
        if not zone_id:
            return []
        
        headers = self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/zones/{zone_id}/dns_records",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                messages = data.get("messages", [])
                errors = data.get("errors", [])
                if messages:
                    error_msg = ", ".join(messages)
                elif errors:
                    error_msg = ", ".join([error.get("message", "未知错误") for error in errors])
                else:
                    error_msg = "未知错误"
                raise Exception(f"Cloudflare API错误: {error_msg}")
            
            records = data.get("result", [])
            return [
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "value": record["content"],
                    "ttl": int(record.get("ttl", 1)),  # Cloudflare的TTL，1表示自动
                    "priority": int(record.get("priority", 0)) if record.get("priority") else None,
                    "status": "active" if record.get("proxied", False) else "inactive"
                }
                for record in records
            ]
    
    async def add_record(self, domain: str, record: Dict[str, Any]) -> str:
        """添加解析记录，返回记录ID"""
        # 首先获取zone_id
        zones = await self.get_domains()
        zone_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                zone_id = zone["id"]
                break
        
        if not zone_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        headers = self._get_headers()
        params = {
            "type": record["type"],
            "name": record["name"],
            "content": record["value"],
            "ttl": record.get("ttl", 1),
            "proxied": False  # 默认不启用CDN代理
        }
        
        if record.get("priority"):
            params["priority"] = record["priority"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/zones/{zone_id}/dns_records",
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                messages = data.get("messages", [])
                errors = data.get("errors", [])
                if messages:
                    error_msg = ", ".join(messages)
                elif errors:
                    error_msg = ", ".join([error.get("message", "未知错误") for error in errors])
                else:
                    error_msg = "未知错误"
                raise Exception(f"Cloudflare API错误: {error_msg}")
            
            record_id = data.get("result", {}).get("id")
            if not record_id:
                raise Exception("服务商API未返回记录ID")
            
            return str(record_id)
    
    async def update_record(self, domain: str, record_id: str, record: Dict[str, Any]) -> bool:
        """更新解析记录"""
        # 首先获取zone_id
        zones = await self.get_domains()
        zone_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                zone_id = zone["id"]
                break
        
        if not zone_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        headers = self._get_headers()
        params = {
            "type": record["type"],
            "name": record["name"],
            "content": record["value"],
            "ttl": record.get("ttl", 1),
            "proxied": False  # 默认不启用CDN代理
        }
        
        if record.get("priority"):
            params["priority"] = record["priority"]
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                json=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                messages = data.get("messages", [])
                errors = data.get("errors", [])
                if messages:
                    error_msg = ", ".join(messages)
                elif errors:
                    error_msg = ", ".join([error.get("message", "未知错误") for error in errors])
                else:
                    error_msg = "未知错误"
                raise Exception(f"Cloudflare API错误: {error_msg}")
            
            return True
    
    async def delete_record(self, domain: str, record_id: str) -> bool:
        """删除解析记录"""
        # 首先获取zone_id
        zones = await self.get_domains()
        zone_id = None
        for zone in zones:
            if zone["name"] == domain or zone["name"] == f"{domain}.":
                zone_id = zone["id"]
                break
        
        if not zone_id:
            raise Exception(f"未找到域名 {domain} 的zone_id")
        
        headers = self._get_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                messages = data.get("messages", [])
                errors = data.get("errors", [])
                if messages:
                    error_msg = ", ".join(messages)
                elif errors:
                    error_msg = ", ".join([error.get("message", "未知错误") for error in errors])
                else:
                    error_msg = "未知错误"
                raise Exception(f"Cloudflare API错误: {error_msg}")
            
            return True
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            await self.get_domains()
            return True
        except Exception as e:
            # 重新抛出异常以便上层处理
            raise e
