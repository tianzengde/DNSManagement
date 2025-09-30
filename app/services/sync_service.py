"""域名同步服务"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from app.models import Provider, Domain, DNSRecord, RecordType
from app.providers.huawei import HuaweiProvider
from app.providers.aliyun import AliyunProvider
from app.providers.tencent import TencentProvider
from app.providers.cloudflare import CloudflareProvider

logger = logging.getLogger(__name__)


class DomainSyncService:
    """域名同步服务"""
    
    def __init__(self):
        self.providers_map = {
            1: HuaweiProvider,  # 华为云
            2: AliyunProvider,  # 阿里云
            3: TencentProvider,  # 腾讯云
            4: CloudflareProvider,  # Cloudflare
        }
    
    async def sync_all_providers(self):
        """同步所有服务商的域名"""
        logger.info("开始同步所有服务商的域名")
        
        try:
            # 获取所有启用的服务商
            providers = await Provider.filter(enabled=True).all()
            
            for provider in providers:
                try:
                    await self.sync_provider_domains(provider)
                except Exception as e:
                    logger.error(f"同步服务商 {provider.name} 失败: {e}")
                    # 更新服务商状态为失败
                    provider.status = "failed"
                    await provider.save()
            
            logger.info("所有服务商域名同步完成")
            
        except Exception as e:
            logger.error(f"同步所有服务商失败: {e}")
    
    async def sync_provider_domains(self, provider: Provider):
        """同步单个服务商的域名"""
        logger.info(f"开始同步服务商 {provider.name} 的域名")
        
        try:
            # 创建服务商实例
            provider_class = self.providers_map.get(provider.type)
            if not provider_class:
                logger.error(f"不支持的服务商类型: {provider.type}")
                return
            
            provider_instance = provider_class(
                access_key=provider.access_key,
                secret_key=provider.secret_key,
                region=provider.region
            )
            
            # 获取域名列表
            domains_data = await provider_instance.get_domains()
            logger.info(f"服务商 {provider.name} 获取到 {len(domains_data)} 个域名")
            
            # 同步域名到数据库
            for domain_data in domains_data:
                await self.sync_domain(provider, domain_data)
            
            # 更新服务商状态为成功
            provider.status = "connected"
            provider.last_test_at = datetime.now()
            await provider.save()
            
            logger.info(f"服务商 {provider.name} 域名同步完成")
            
        except Exception as e:
            logger.error(f"同步服务商 {provider.name} 域名失败: {e}")
            # 更新服务商状态为失败
            provider.status = "failed"
            await provider.save()
            raise
    
    async def sync_domain(self, provider: Provider, domain_data: Dict[str, Any]):
        """同步单个域名"""
        try:
            domain_name = domain_data.get('name', '').rstrip('.')
            if not domain_name:
                return
            
            # 首先检查域名是否已存在
            existing_domain = await Domain.filter(name=domain_name).prefetch_related('provider').first()
            
            if existing_domain:
                # 如果域名已存在，检查是否属于当前服务商
                if existing_domain.provider_id == provider.id:
                    logger.info(f"更新现有域名: {domain_name}")
                    domain = existing_domain
                else:
                    # 域名属于其他服务商，跳过同步
                    logger.warning(f"域名 {domain_name} 已属于服务商 {existing_domain.provider.name}，跳过同步")
                    return
            else:
                # 创建新域名记录
                domain = await Domain.create(
                    name=domain_name,
                    provider=provider,
                    enabled=True,
                    auto_update=True
                )
                logger.info(f"创建新域名: {domain_name}")
            
            # 获取该域名的DNS记录
            try:
                provider_instance = self.providers_map[provider.type](
                    access_key=provider.access_key,
                    secret_key=provider.secret_key,
                    region=provider.region
                )
                
                records_data = await provider_instance.get_records(domain_name)
                logger.info(f"域名 {domain_name} 获取到 {len(records_data)} 条DNS记录")
                
                # 同步DNS记录
                await self.sync_dns_records(domain, records_data)
                
            except Exception as e:
                logger.error(f"获取域名 {domain_name} 的DNS记录失败: {e}")
            
        except Exception as e:
            logger.error(f"同步域名失败: {e}")
    
    async def sync_dns_records(self, domain: Domain, records_data: List[Dict[str, Any]]):
        """同步DNS记录"""
        try:
            # 获取现有的DNS记录
            existing_records = await DNSRecord.filter(domain=domain).all()
            existing_records_map = {f"{r.name}_{r.type}": r for r in existing_records}
            
            # 处理新的记录数据
            new_records_map = {}
            for record_data in records_data:
                record_name = record_data.get('name', '').rstrip('.')
                record_type = self._get_record_type(record_data.get('type', ''))
                # 阿里云返回的是 'value' 字段，华为云可能返回 'records' 字段
                record_value = record_data.get('value') or record_data.get('records', [])
                external_id = record_data.get('id', '')
                
                logger.debug(f"处理DNS记录: name={record_name}, type={record_type}, value={record_value}, external_id={external_id}")
                
                if not record_name or not record_type or not record_value:
                    logger.warning(f"跳过无效记录: name={record_name}, type={record_type}, value={record_value}")
                    continue
                
                # 合并多个记录值
                if isinstance(record_value, list):
                    record_value = ','.join(record_value)
                
                key = f"{record_name}_{record_type}"
                new_records_map[key] = {
                    'name': record_name,
                    'type': record_type,
                    'value': record_value,
                    'ttl': record_data.get('ttl', 600),
                    'priority': record_data.get('priority'),
                    'enabled': True,
                    'external_id': external_id
                }
            
            # 更新或创建记录
            for key, record_data in new_records_map.items():
                if key in existing_records_map:
                    # 更新现有记录
                    existing_record = existing_records_map[key]
                    await existing_record.update_from_dict({
                        'value': record_data['value'],
                        'ttl': record_data['ttl'],
                        'priority': record_data['priority'],
                        'external_id': record_data['external_id']
                    })
                else:
                    # 创建新记录
                    await DNSRecord.create(
                        domain=domain,
                        **record_data
                    )
            
            # 删除不再存在的记录
            for key, existing_record in existing_records_map.items():
                if key not in new_records_map:
                    await existing_record.delete()
            
            logger.info(f"域名 {domain.name} 的DNS记录同步完成")
            
        except Exception as e:
            logger.error(f"同步DNS记录失败: {e}")
    
    def _get_record_type(self, type_str: str) -> RecordType:
        """将字符串类型转换为RecordType枚举"""
        if not type_str:
            return RecordType.A
        
        type_mapping = {
            'A': RecordType.A,
            'AAAA': RecordType.AAAA,
            'CNAME': RecordType.CNAME,
            'MX': RecordType.MX,
            'TXT': RecordType.TXT,
            'NS': RecordType.NS,
        }
        return type_mapping.get(type_str.upper(), RecordType.A)
    
    async def sync_single_provider(self, provider_id: int):
        """同步单个服务商"""
        try:
            provider = await Provider.get(id=provider_id)
            await self.sync_provider_domains(provider)
        except Exception as e:
            logger.error(f"同步服务商 {provider_id} 失败: {e}")
            raise
