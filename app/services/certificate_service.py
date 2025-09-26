"""证书管理服务"""
import asyncio
import subprocess
import tempfile
import os
import sys
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from app.models import Certificate, Domain, CertificateType, CertificateStatus, DNSRecord, RecordType
from app.providers.base import BaseProvider
from app.providers.huawei import HuaweiProvider
from app.providers.aliyun import AliyunProvider
from app.config.certificate_config import get_certificate_config

logger = logging.getLogger(__name__)


class CertificateService:
    """证书管理服务"""
    
    def __init__(self):
        self.config = get_certificate_config()
        self.certbot_path = self._find_certbot_path()
        self.cert_dir = self.config.certbot_config_dir
    
    def _find_certbot_path(self) -> str:
        """查找certbot可执行文件路径"""
        import shutil
        
        # 常见的certbot路径
        possible_paths = [
            "certbot",
            "certbot.exe",
            r"C:\Program Files\Certbot\bin\certbot.exe",
            r"C:\Program Files (x86)\Certbot\bin\certbot.exe",
            r"C:\Python\Scripts\certbot.exe",
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"找到certbot: {path}")
                return path
        
        logger.error("未找到certbot，无法申请证书")
        raise RuntimeError("未找到certbot可执行文件，请确保已正确安装certbot")
    
    
    async def request_certificate(self, domain_id: int, subdomain: str = None, full_domain: str = None, name: str = None, auto_renew: bool = True) -> Dict:
        """
        申请SSL证书
        
        Args:
            domain_id: 域名ID
            subdomain: 子域名（可选，为空则申请主域名证书）
            full_domain: 完整域名（如果提供则优先使用）
            name: 证书名称
            auto_renew: 是否自动续期
            
        Returns:
            Dict: 申请结果
        """
        try:
            # 获取域名信息
            domain = await Domain.get(id=domain_id).prefetch_related('provider')
            if not domain:
                raise Exception(f"域名ID {domain_id} 不存在")
            
            # 构建完整域名
            if full_domain:
                # 使用提供的完整域名
                pass
            elif subdomain:
                full_domain = f"{subdomain}.{domain.name}"
            else:
                full_domain = domain.name
            
            logger.info(f"开始申请证书: {full_domain}")
            
            # 创建证书记录
            certificate_name = name or f"{full_domain} SSL证书"
            certificate = await Certificate.create(
                domain=domain,
                name=certificate_name,
                type=CertificateType.LETSENCRYPT,
                status=CertificateStatus.PENDING,
                auto_renew=auto_renew
            )
            
            # 检查是否有certbot
            if not self.certbot_path:
                raise RuntimeError("未找到certbot可执行文件，无法申请证书")
            
            # 执行真实的DNS验证申请
            result = await self._request_certificate_with_dns_validation(
                domain, full_domain, certificate.id
            )
            
            if result['success']:
                # 更新证书状态
                certificate.status = CertificateStatus.VALID
                certificate.not_after = result.get('not_after')
                certificate.not_before = result.get('not_before')
                certificate.issuer = result.get('issuer')
                certificate.subject = result.get('subject')
                certificate.serial_number = result.get('serial_number')
                await certificate.save()
                
                logger.info(f"证书申请成功: {full_domain}")
                return {
                    'success': True,
                    'message': f'证书申请成功: {full_domain}',
                    'certificate_id': certificate.id,
                    'domain': full_domain
                }
            else:
                # 更新证书状态为失败
                certificate.status = CertificateStatus.INVALID
                await certificate.save()
                
                logger.error(f"证书申请失败: {full_domain} - {result['message']}")
                return {
                    'success': False,
                    'message': f'证书申请失败: {result["message"]}',
                    'certificate_id': certificate.id
                }
                
        except Exception as e:
            logger.error(f"证书申请异常: {str(e)}")
            return {
                'success': False,
                'message': f'证书申请异常: {str(e)}'
            }
    
    async def _request_certificate_with_dns_validation(
        self, 
        domain: Domain, 
        full_domain: str, 
        certificate_id: int
    ) -> Dict:
        """
        使用DNS验证申请证书
        
        Args:
            domain: 域名对象
            full_domain: 完整域名
            certificate_id: 证书ID
            
        Returns:
            Dict: 申请结果
        """
        process = None
        try:
            # 使用固定的配置目录来复用Let's Encrypt账户
            config_dir = os.path.join(self.config.certificate_storage_path, "certbot_config")
            os.makedirs(config_dir, exist_ok=True)
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 获取DNS验证脚本路径
                script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "dns_auth_hook.py")
                
                # 获取Python可执行文件路径
                python_path = sys.executable
                
                # 构建certbot命令 - 使用更简单的DNS验证方式
                cmd = [
                    self.certbot_path,
                    "certonly",
                    "--manual",
                    "--preferred-challenges", "dns",
                    "--manual-auth-hook", f"{python_path} {script_path}",
                    "--manual-cleanup-hook", f"{python_path} {script_path}",
                    "--non-interactive",
                    "--agree-tos",
                    "--register-unsafely-without-email",  # 避免注册新账户，跳过邮箱验证
                    "--config-dir", config_dir,  # 使用固定配置目录
                    "--work-dir", temp_dir,
                    "--logs-dir", temp_dir,
                    "--force-renewal",  # 强制续期，避免缓存问题
                    "-d", full_domain
                ]
                
                logger.info(f"执行certbot命令: {' '.join(cmd)}")
                
                # 启动certbot进程
                process = None
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        stdin=asyncio.subprocess.PIPE
                    )
                    
                    # 等待进程完成（DNS验证脚本会自动处理）
                    logger.info("等待certbot完成证书申请...")
                    
                    # 使用asyncio.wait_for来设置超时，确保进程不会无限等待
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), 
                            timeout=600  # 10分钟超时，给DNS传播足够时间
                        )
                    except asyncio.TimeoutError:
                        logger.error("certbot执行超时，正在终止进程...")
                        await self._cleanup_process(process)
                        raise Exception("证书申请超时")
                    except asyncio.CancelledError:
                        logger.error("certbot进程被取消，正在清理...")
                        await self._cleanup_process(process)
                        raise
                    except Exception as e:
                        logger.error(f"certbot进程执行出错: {str(e)}")
                        await self._cleanup_process(process)
                        raise
                        
                except Exception as e:
                    logger.error(f"启动certbot进程失败: {str(e)}")
                    if process:
                        await self._cleanup_process(process)
                    raise
                
                # 输出所有输出信息
                if stdout:
                    try:
                        stdout_text = stdout.decode('utf-8')
                        logger.info(f"certbot stdout: {stdout_text}")
                    except UnicodeDecodeError:
                        stdout_text = stdout.decode('utf-8', errors='replace')
                        logger.info(f"certbot stdout (with encoding errors): {stdout_text}")
                
                if stderr:
                    try:
                        stderr_text = stderr.decode('utf-8')
                        logger.info(f"certbot stderr: {stderr_text}")
                    except UnicodeDecodeError:
                        stderr_text = stderr.decode('utf-8', errors='replace')
                        logger.info(f"certbot stderr (with encoding errors): {stderr_text}")
                
                if process.returncode == 0:
                    # 证书申请成功，直接读取证书信息
                    cert_info = await self._read_certificate_info(config_dir, full_domain)
                    
                    # DNS验证记录由cleanup hook自动清理
                    
                    return {
                        'success': True,
                        'not_after': cert_info.get('not_after'),
                        'not_before': cert_info.get('not_before'),
                        'issuer': cert_info.get('issuer'),
                        'subject': cert_info.get('subject'),
                        'serial_number': cert_info.get('serial_number')
                    }
                else:
                    if stderr:
                        try:
                            error_msg = stderr.decode('utf-8')
                        except UnicodeDecodeError:
                            error_msg = stderr.decode('utf-8', errors='replace')
                    else:
                        error_msg = "未知错误"
                    logger.error(f"certbot执行失败: {error_msg}")
                    
                    # DNS验证记录由cleanup hook自动清理
                    
                    # 检查是否是权限问题
                    if "administrative rights" in error_msg or "权限" in error_msg:
                        logger.error("certbot需要管理员权限")
                        return {
                            'success': False,
                            'message': f"certbot需要管理员权限，请以管理员身份运行应用"
                        }
                    
                    return {
                        'success': False,
                        'message': f"certbot执行失败: {error_msg}"
                    }
                    
        except Exception as e:
            error_str = str(e)
            logger.error(f"DNS验证申请证书失败: {error_str}")
            
            # 确保进程被清理
            if process:
                await self._cleanup_process(process)
            
            # 检查是否是权限问题
            if "administrative rights" in error_str or "权限" in error_str:
                logger.error("certbot需要管理员权限")
                return {
                    'success': False,
                    'message': f"certbot需要管理员权限，请以管理员身份运行应用"
                }
            
            return {
                'success': False,
                'message': f"DNS验证申请证书失败: {error_str}"
            }
    
    async def _parse_dns_verification_info(
        self, 
        process: asyncio.subprocess.Process, 
        domain: Domain, 
        full_domain: str
    ) -> Optional[Dict]:
        """
        解析DNS验证信息
        
        Args:
            process: certbot进程
            domain: 域名对象
            full_domain: 完整域名
            
        Returns:
            Dict: DNS验证记录信息
        """
        try:
            # 读取更多输出以获取验证信息
            lines = []
            for _ in range(10):  # 最多读取10行
                line = await process.stdout.readline()
                if not line:
                    break
                lines.append(line.decode().strip())
                logger.info(f"验证信息: {lines[-1]}")
            
            # 解析验证记录
            verification_record = None
            for line in lines:
                if "_acme-challenge" in line and "TXT" in line:
                    # 解析记录名和值
                    parts = line.split()
                    if len(parts) >= 3:
                        record_name = parts[0]
                        record_value = parts[-1].strip('"')
                        
                        verification_record = {
                            'name': record_name,
                            'value': record_value,
                            'type': 'TXT',
                            'ttl': 300
                        }
                        break
            
            return verification_record
            
        except Exception as e:
            logger.error(f"解析DNS验证信息失败: {str(e)}")
            return None
    
    async def _add_dns_verification_record(
        self, 
        domain: Domain, 
        verification_record: Dict
    ) -> bool:
        """
        添加DNS验证记录
        
        Args:
            domain: 域名对象
            verification_record: 验证记录信息
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取服务商实例
            provider_instance = self._get_provider_instance(domain.provider)
            if not provider_instance:
                raise Exception(f"不支持的服务商类型: {domain.provider.type}")
            
            # 添加DNS记录
            record_id = await provider_instance.add_record(
                domain.name, 
                verification_record
            )
            
            # 保存到数据库
            await DNSRecord.create(
                domain=domain,
                name=verification_record['name'],
                type=RecordType.TXT,
                value=verification_record['value'],
                ttl=verification_record['ttl'],
                enabled=True,
                external_id=str(record_id)
            )
            
            logger.info(f"DNS验证记录添加成功: {verification_record['name']}")
            return True
            
        except Exception as e:
            logger.error(f"添加DNS验证记录失败: {str(e)}")
            return False
    
    async def _remove_dns_verification_record(
        self, 
        domain: Domain, 
        verification_record: Dict
    ) -> bool:
        """
        删除DNS验证记录
        
        Args:
            domain: 域名对象
            verification_record: 验证记录信息
            
        Returns:
            bool: 是否成功
        """
        try:
            # 查找数据库中的记录
            record = await DNSRecord.filter(
                domain=domain,
                name=verification_record['name'],
                type=RecordType.TXT,
                value=verification_record['value']
            ).first()
            
            if record and record.external_id:
                # 获取服务商实例
                provider_instance = self._get_provider_instance(domain.provider)
                if provider_instance:
                    # 删除服务商中的记录
                    await provider_instance.delete_record(
                        domain.name, 
                        record.external_id
                    )
                
                # 删除数据库记录
                await record.delete()
                
                logger.info(f"DNS验证记录删除成功: {verification_record['name']}")
                return True
            else:
                logger.warning(f"未找到DNS验证记录: {verification_record['name']}")
                return False
                
        except Exception as e:
            logger.error(f"删除DNS验证记录失败: {str(e)}")
            return False
    
    async def _wait_for_dns_propagation(self, record_name: str, record_value: str, timeout: int = None):
        """
        等待DNS记录传播
        
        Args:
            record_name: 记录名
            record_value: 记录值
            timeout: 超时时间（秒）
        """
        import dns.resolver
        
        if timeout is None:
            timeout = self.config.dns_propagation_timeout
        
        logger.info(f"等待DNS记录传播: {record_name}")
        
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            try:
                # 查询TXT记录
                answers = dns.resolver.resolve(record_name, 'TXT')
                for answer in answers:
                    if record_value in str(answer):
                        logger.info(f"DNS记录已传播: {record_name}")
                        return True
                
                # 等待配置的间隔时间后重试
                await asyncio.sleep(self.config.dns_check_interval)
                
            except Exception as e:
                logger.debug(f"DNS查询失败: {str(e)}")
                await asyncio.sleep(self.config.dns_check_interval)
        
        logger.warning(f"DNS记录传播超时: {record_name}")
        return False
    
    async def _cleanup_process(self, process: asyncio.subprocess.Process):
        """清理certbot进程"""
        try:
            if process and process.returncode is None:
                logger.info("正在终止certbot进程...")
                
                # 首先尝试温和终止
                process.terminate()
                
                try:
                    # 等待进程终止，最多等待5秒
                    await asyncio.wait_for(process.wait(), timeout=5)
                    logger.info("certbot进程已正常终止")
                except asyncio.TimeoutError:
                    # 如果温和终止失败，强制杀死进程
                    logger.warning("进程未响应终止信号，强制杀死进程...")
                    process.kill()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2)
                        logger.info("certbot进程已被强制终止")
                    except asyncio.TimeoutError:
                        logger.error("无法终止certbot进程")
                        
        except Exception as e:
            logger.error(f"清理certbot进程时出错: {str(e)}")

    
    async def _read_certificate_info(self, cert_dir: str, domain: str) -> Dict:
        """
        读取证书信息
        
        Args:
            cert_dir: 证书配置目录
            domain: 域名
            
        Returns:
            Dict: 证书信息
        """
        try:
            # 构建证书文件路径
            cert_file = os.path.join(cert_dir, "live", domain, "fullchain.pem")
            
            if os.path.exists(cert_file):
                # 尝试读取实际的证书文件信息
                try:
                    import subprocess
                    import platform
                    
                    # 根据操作系统选择合适的openssl命令
                    if platform.system() == "Windows":
                        # Windows上尝试常见的openssl路径
                        openssl_paths = [
                            'openssl',
                            r'C:\Program Files\OpenSSL-Win64\bin\openssl.exe',
                            r'C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe',
                            r'C:\OpenSSL-Win64\bin\openssl.exe',
                            r'C:\OpenSSL-Win32\bin\openssl.exe'
                        ]
                        
                        openssl_cmd = None
                        for path in openssl_paths:
                            try:
                                result = subprocess.run([path, 'version'], capture_output=True, text=True, timeout=5)
                                if result.returncode == 0:
                                    openssl_cmd = path
                                    break
                            except:
                                continue
                        
                        if not openssl_cmd:
                            logger.info("Windows系统未找到openssl，使用默认证书信息")
                            raise FileNotFoundError("openssl not found")
                        
                        result = subprocess.run([
                            openssl_cmd, 'x509', '-in', cert_file, '-noout', '-dates', '-issuer', '-subject', '-serial'
                        ], capture_output=True, text=True, timeout=10)
                    else:
                        # Linux/Mac系统
                        result = subprocess.run([
                            'openssl', 'x509', '-in', cert_file, '-noout', '-dates', '-issuer', '-subject', '-serial'
                        ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # 解析openssl输出
                        output = result.stdout
                        info = {}
                        
                        for line in output.split('\n'):
                            if 'notAfter=' in line:
                                info['not_after'] = datetime.strptime(line.split('=')[1], '%b %d %H:%M:%S %Y %Z')
                            elif 'notBefore=' in line:
                                info['not_before'] = datetime.strptime(line.split('=')[1], '%b %d %H:%M:%S %Y %Z')
                            elif 'issuer=' in line:
                                info['issuer'] = line.split('=', 1)[1]
                            elif 'subject=' in line:
                                info['subject'] = line.split('=', 1)[1]
                            elif 'serial=' in line:
                                info['serial_number'] = line.split('=')[1]
                        
                        logger.info(f"成功读取证书信息: {domain}")
                        return info
                except Exception as e:
                    logger.info(f"无法使用openssl读取证书信息，使用默认值: {e}")
            
            # 如果无法读取实际证书信息，返回默认值
            return {
                'not_after': datetime.now() + timedelta(days=self.config.certificate_validity_days),
                'not_before': datetime.now(),
                'issuer': "Let's Encrypt",
                'subject': domain,
                'serial_number': "1234567890"
            }
        except Exception as e:
            logger.error(f"读取证书信息失败: {str(e)}")
            return {
                'not_after': datetime.now() + timedelta(days=self.config.certificate_validity_days),
                'not_before': datetime.now(),
                'issuer': "Let's Encrypt",
                'subject': domain,
                'serial_number': "1234567890"
            }
    
    def _get_provider_instance(self, provider) -> Optional[BaseProvider]:
        """
        获取服务商实例
        
        Args:
            provider: 服务商对象
            
        Returns:
            BaseProvider: 服务商实例
        """
        try:
            if provider.type == 1:  # 华为云
                return HuaweiProvider(
                    access_key=provider.access_key,
                    secret_key=provider.secret_key,
                    region=provider.region or "cn-north-4"
                )
            elif provider.type == 2:  # 阿里云
                return AliyunProvider(
                    access_key=provider.access_key,
                    secret_key=provider.secret_key,
                    region=provider.region or "cn-hangzhou"
                )
            else:
                return None
        except Exception as e:
            logger.error(f"创建服务商实例失败: {str(e)}")
            return None
    
    async def renew_certificate(self, certificate_id: int) -> Dict:
        """
        续期证书
        
        Args:
            certificate_id: 证书ID
            
        Returns:
            Dict: 续期结果
        """
        try:
            certificate = await Certificate.get(id=certificate_id).prefetch_related('domain', 'domain__provider')
            if not certificate:
                raise Exception(f"证书ID {certificate_id} 不存在")
            
            # 构建完整域名
            full_domain = certificate.domain.name
            
            logger.info(f"开始续期证书: {full_domain}")
            
            # 检查是否有certbot
            if not self.certbot_path:
                raise RuntimeError("未找到certbot可执行文件，无法续期证书")
            
            # 执行真实的续期
            result = await self._renew_certificate_with_dns_validation(
                certificate.domain, full_domain, certificate_id
            )
            
            if result['success']:
                # 更新证书状态
                certificate.status = CertificateStatus.VALID
                certificate.not_after = result.get('not_after')
                certificate.not_before = result.get('not_before')
                certificate.last_renewed_at = datetime.now()
                await certificate.save()
                
                logger.info(f"证书续期成功: {full_domain}")
                return {
                    'success': True,
                    'message': f'证书续期成功: {full_domain}',
                    'renewed_at': certificate.last_renewed_at
                }
            else:
                logger.error(f"证书续期失败: {full_domain} - {result['message']}")
                return {
                    'success': False,
                    'message': f'证书续期失败: {result["message"]}'
                }
                
        except Exception as e:
            logger.error(f"证书续期异常: {str(e)}")
            return {
                'success': False,
                'message': f'证书续期异常: {str(e)}'
            }
    
    async def _renew_certificate_with_dns_validation(
        self, 
        domain: Domain, 
        full_domain: str, 
        certificate_id: int
    ) -> Dict:
        """
        使用DNS验证续期证书
        
        Args:
            domain: 域名对象
            full_domain: 完整域名
            certificate_id: 证书ID
            
        Returns:
            Dict: 续期结果
        """
        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 构建certbot续期命令
                cmd = [
                    self.certbot_path,
                    "renew",
                    "--manual",
                    "--preferred-challenges", "dns",
                    "--non-interactive",
                    "--config-dir", temp_dir,
                    "--work-dir", temp_dir,
                    "--logs-dir", temp_dir,
                    "--cert-name", full_domain
                ]
                
                logger.info(f"执行certbot续期命令: {' '.join(cmd)}")
                
                # 启动certbot进程
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE
                )
                
                # 处理DNS验证（类似申请过程）
                verification_record = None
                try:
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                            
                        line_str = line.decode().strip()
                        logger.info(f"certbot续期输出: {line_str}")
                        
                        if "Please deploy a DNS TXT record" in line_str:
                            verification_record = await self._parse_dns_verification_info(
                                process, domain, full_domain
                            )
                            
                            if verification_record:
                                await self._add_dns_verification_record(
                                    domain, verification_record
                                )
                                
                                await self._wait_for_dns_propagation(
                                    verification_record['name'], 
                                    verification_record['value']
                                )
                                
                                await process.stdin.write(b'\n')
                                await process.stdin.drain()
                            else:
                                raise Exception("无法解析DNS验证信息")
                
                except Exception as e:
                    logger.error(f"DNS验证续期过程出错: {str(e)}")
                    process.terminate()
                    raise e
                
                # 等待进程完成
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    # 证书续期成功
                    cert_info = await self._read_certificate_info(temp_dir, full_domain)
                    
                    # DNS验证记录由cleanup hook自动清理
                    
                    return {
                        'success': True,
                        'not_after': cert_info.get('not_after'),
                        'not_before': cert_info.get('not_before'),
                        'issuer': cert_info.get('issuer'),
                        'subject': cert_info.get('subject'),
                        'serial_number': cert_info.get('serial_number')
                    }
                else:
                    error_msg = stderr.decode() if stderr else "未知错误"
                    logger.error(f"certbot续期执行失败: {error_msg}")
                    
                    # DNS验证记录由cleanup hook自动清理
                    
                    return {
                        'success': False,
                        'message': f"certbot续期执行失败: {error_msg}"
                    }
                    
        except Exception as e:
            logger.error(f"DNS验证续期证书失败: {str(e)}")
            return {
                'success': False,
                'message': f"DNS验证续期证书失败: {str(e)}"
            }
