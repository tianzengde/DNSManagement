"""证书管理配置"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class CertificateConfig(BaseSettings):
    """证书管理配置"""
    
    # Certbot配置
    certbot_path: str = "certbot"
    certbot_config_dir: str = "/etc/letsencrypt"
    certbot_work_dir: str = "/var/lib/letsencrypt"
    certbot_logs_dir: str = "/var/log/letsencrypt"
    
    # 证书配置
    certificate_email: str = "example@example.com"
    certificate_rsa_key_size: int = 2048
    certificate_validity_days: int = 90
    
    # DNS验证配置
    dns_propagation_timeout: int = 300  # DNS传播等待时间（秒）
    dns_check_interval: int = 10  # DNS检查间隔（秒）
    
    # 自动续期配置
    auto_renewal_days: int = 30  # 提前续期天数
    auto_renewal_enabled: bool = True
    
    # 证书存储配置
    certificate_storage_path: str = "./data/certificates"
    
    # 强制使用真实模式（跳过模拟模式）
    force_real_mode: bool = False
    
    class Config:
        env_prefix = "CERTIFICATE_"
        env_file = ".env"


# 创建全局配置实例
certificate_config = CertificateConfig()


def get_certificate_config() -> CertificateConfig:
    """获取证书配置"""
    return certificate_config


def setup_certificate_directories():
    """设置证书相关目录"""
    directories = [
        certificate_config.certificate_storage_path,
        certificate_config.certbot_config_dir,
        certificate_config.certbot_work_dir,
        certificate_config.certbot_logs_dir,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # 在Windows上不需要设置权限
        try:
            os.chmod(directory, 0o755)
        except (OSError, PermissionError):
            # Windows上可能无法设置权限，忽略错误
            pass
