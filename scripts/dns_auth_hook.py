#!/usr/bin/env python3
"""
DNS验证脚本 - 用于certbot的manual-auth-hook
"""
import sys
import os
import json
import asyncio
import httpx
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Domain, DNSRecord
from app.providers.huawei import HuaweiProvider
from app.providers.aliyun import AliyunProvider
from app.database import init_database, close_database


async def add_dns_record(domain_name: str, record_name: str, record_value: str):
    """添加DNS验证记录"""
    try:
        print(f"INFO: 开始添加DNS记录 - 域名: {domain_name}, 记录名: {record_name}, 值: {record_value}")
        
        # 初始化数据库
        print("INFO: 初始化数据库连接...")
        await init_database()
        print("INFO: 数据库连接成功")
        
        # 查找域名
        print(f"INFO: 查找域名 {domain_name}...")
        domain = await Domain.filter(name=domain_name).prefetch_related('provider').first()
        if not domain:
            print(f"ERROR: 未找到域名 {domain_name}")
            return False
        print(f"INFO: 找到域名 {domain_name}, 服务商类型: {domain.provider.type}")
        
        # 获取服务商实例
        provider_instance = None
        if domain.provider.type == 1:  # 华为云
            provider_instance = HuaweiProvider(
                access_key=domain.provider.access_key,
                secret_key=domain.provider.secret_key,
                region=domain.provider.region or "cn-north-4"
            )
        elif domain.provider.type == 2:  # 阿里云
            provider_instance = AliyunProvider(
                access_key=domain.provider.access_key,
                secret_key=domain.provider.secret_key,
                region=domain.provider.region or "cn-hangzhou"
            )
        
        if not provider_instance:
            print(f"ERROR: 不支持的服务商类型 {domain.provider.type}")
            return False
        
        # 构建记录数据
        record_data = {
            "name": record_name,
            "type": "TXT",
            "value": f'"{record_value}"',  # TXT记录值需要用引号包围
            "ttl": 300
        }
        print(f"INFO: 准备添加DNS记录数据: {record_data}")
        
        # 检查是否已存在相同名称的DNS记录
        print("INFO: 检查是否已存在相同名称的DNS记录...")
        existing_records = await provider_instance.get_records(domain_name)
        existing_record = None
        
        for record in existing_records:
            if record.get("name") == record_name and record.get("type") == "TXT":
                existing_record = record
                break
        
        record_id = None
        if existing_record:
            # 更新现有记录
            print(f"INFO: 找到现有记录，更新值: {existing_record.get('id')}")
            success = await provider_instance.update_record(domain_name, existing_record["id"], record_data)
            if success:
                record_id = existing_record["id"]
                print(f"SUCCESS: DNS记录更新成功 {record_name} -> {record_value}")
            else:
                print(f"ERROR: DNS记录更新失败")
                return False
        else:
            # 添加新记录
            print("INFO: 添加新的DNS记录...")
            try:
                record_id = await provider_instance.add_record(domain_name, record_data)
                if record_id:
                    print(f"SUCCESS: DNS记录添加成功 {record_name} -> {record_value}, 记录ID: {record_id}")
                else:
                    print(f"ERROR: DNS记录添加失败")
                    return False
            except Exception as api_error:
                error_str = str(api_error)
                if "Duplicate record set exists" in error_str or "重复" in error_str:
                    print(f"INFO: DNS记录已存在，视为成功: {record_name}")
                    # 重新获取记录ID
                    updated_records = await provider_instance.get_records(domain_name)
                    for record in updated_records:
                        if record.get("name") == record_name and record.get("type") == "TXT":
                            record_id = record["id"]
                            break
                else:
                    print(f"ERROR: 添加DNS记录时出错: {error_str}")
                    return False
        
        # 保存到本地数据库
        if record_id:
            print("INFO: 保存DNS记录到本地数据库...")
            try:
                # 检查本地是否已存在
                local_record = await DNSRecord.filter(
                    domain=domain,
                    name=record_name,
                    type=5  # TXT类型
                ).first()
                
                if local_record:
                    # 更新现有记录
                    local_record.value = record_value.strip('"')  # 去掉引号
                    local_record.external_id = str(record_id)
                    await local_record.save()
                    print(f"INFO: 本地DNS记录已更新: {local_record.id}")
                else:
                    # 创建新记录
                    local_record = await DNSRecord.create(
                        domain=domain,
                        name=record_name,
                        type=5,  # TXT类型
                        value=record_value.strip('"'),  # 去掉引号
                        ttl=300,
                        enabled=True,
                        external_id=str(record_id)
                    )
                    print(f"INFO: 本地DNS记录已创建: {local_record.id}")
                    
            except Exception as db_error:
                print(f"WARNING: 保存到本地数据库失败: {str(db_error)}")
        
        # 等待DNS传播
        print("INFO: 等待DNS记录传播...")
        import asyncio
        await asyncio.sleep(30)  # 等待30秒让DNS传播
        print("INFO: DNS传播等待完成")
        
        return True
            
    except Exception as e:
        print(f"ERROR: 添加DNS记录时出错: {str(e)}")
        return False


async def cleanup_dns_record(domain_name: str, record_name: str, record_value: str):
    """清理DNS验证记录"""
    try:
        print(f"INFO: 开始清理DNS记录 - 域名: {domain_name}, 记录名: {record_name}")
        
        # 初始化数据库
        await init_database()
        
        # 查找域名
        domain = await Domain.filter(name=domain_name).prefetch_related('provider').first()
        if not domain:
            print(f"ERROR: 未找到域名 {domain_name}")
            return False
        
        # 获取服务商实例
        provider_instance = None
        if domain.provider.type == 1:  # 华为云
            provider_instance = HuaweiProvider(
                access_key=domain.provider.access_key,
                secret_key=domain.provider.secret_key,
                region=domain.provider.region or "cn-north-4"
            )
        elif domain.provider.type == 2:  # 阿里云
            provider_instance = AliyunProvider(
                access_key=domain.provider.access_key,
                secret_key=domain.provider.secret_key,
                region=domain.provider.region or "cn-hangzhou"
            )
        
        if not provider_instance:
            print(f"ERROR: 不支持的服务商类型 {domain.provider.type}")
            return False
        
        # 先从本地数据库查找记录
        print("INFO: 从本地数据库查找DNS记录...")
        local_record = await DNSRecord.filter(
            domain=domain,
            name=record_name,
            type=5  # TXT类型
        ).first()
        
        deleted_from_provider = False
        
        if local_record and local_record.external_id:
            # 使用本地记录的external_id删除
            print(f"INFO: 使用本地记录ID删除: {local_record.external_id}")
            try:
                success = await provider_instance.delete_record(domain_name, local_record.external_id)
                if success:
                    print(f"SUCCESS: DNS记录删除成功 {record_name}")
                    deleted_from_provider = True
                else:
                    print(f"WARNING: 使用本地记录ID删除失败，尝试搜索删除")
            except Exception as e:
                print(f"WARNING: 使用本地记录ID删除出错: {str(e)}，尝试搜索删除")
        
        # 如果本地记录删除失败，尝试搜索删除
        if not deleted_from_provider:
            print("INFO: 搜索服务商DNS记录进行删除...")
            try:
                records = await provider_instance.get_records(domain_name)
                for record in records:
                    if record.get("name") == record_name and record.get("type") == "TXT":
                        print(f"INFO: 找到要删除的DNS记录: {record.get('id')}")
                        success = await provider_instance.delete_record(domain_name, record["id"])
                        if success:
                            print(f"SUCCESS: DNS记录删除成功 {record_name}")
                            deleted_from_provider = True
                            break
                        else:
                            print(f"ERROR: DNS记录删除失败")
                
                if not deleted_from_provider:
                    print(f"WARNING: 未找到要删除的DNS记录 {record_name}")
            except Exception as e:
                print(f"ERROR: 搜索删除DNS记录时出错: {str(e)}")
        
        # 删除本地数据库记录
        if local_record:
            print("INFO: 删除本地数据库记录...")
            try:
                await local_record.delete()
                print(f"SUCCESS: 本地DNS记录删除成功: {local_record.id}")
            except Exception as e:
                print(f"ERROR: 删除本地DNS记录失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: 删除DNS记录时出错: {str(e)}")
        return False


async def main():
    """主函数"""
    # certbot manual-auth-hook 通过环境变量传递参数：
    # CERTBOT_DOMAIN: 要验证的域名
    # CERTBOT_VALIDATION: 验证令牌
    # CERTBOT_TOKEN: 验证令牌（与CERTBOT_VALIDATION相同）
    
    # 从环境变量获取参数
    domain = os.environ.get('CERTBOT_DOMAIN')
    validation_token = os.environ.get('CERTBOT_VALIDATION') or os.environ.get('CERTBOT_TOKEN')
    
    print(f"DEBUG: 环境变量 CERTBOT_DOMAIN = {domain}")
    print(f"DEBUG: 环境变量 CERTBOT_VALIDATION = {validation_token}")
    print(f"DEBUG: 环境变量 CERTBOT_AUTH_OUTPUT = {os.environ.get('CERTBOT_AUTH_OUTPUT')}")
    
    if not domain or not validation_token:
        print("ERROR: Missing required environment variables CERTBOT_DOMAIN and CERTBOT_VALIDATION")
        print(f"CERTBOT_DOMAIN: {domain}")
        print(f"CERTBOT_VALIDATION: {validation_token}")
        sys.exit(1)
    
    # 从域名中提取主域名（去掉子域名）
    domain_parts = domain.split('.')
    if len(domain_parts) >= 2:
        main_domain = '.'.join(domain_parts[-2:])  # 取最后两部分作为主域名
    else:
        main_domain = domain
    
    # 构建DNS记录名
    record_name = f"_acme-challenge.{domain}"
    
    # 根据环境变量判断是添加还是清理
    if os.environ.get('CERTBOT_AUTH_OUTPUT'):
        # 这是cleanup hook
        success = await cleanup_dns_record(main_domain, record_name, validation_token)
    else:
        # 这是auth hook
        success = await add_dns_record(main_domain, record_name, validation_token)
    
    # 关闭数据库连接
    try:
        await close_database()
        print("INFO: 数据库连接已关闭")
    except Exception as e:
        print(f"WARNING: 关闭数据库连接时出错: {str(e)}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
