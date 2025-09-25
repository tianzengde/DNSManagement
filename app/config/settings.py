"""应用配置"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""
    
    # 应用配置
    app_name: str = "DNS证书管理系统"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # 数据库配置
    database_url: str = "sqlite://./data/dns_management.db"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 安全配置
    secret_key: str = "your-secret-key-here"
    
    # 定时任务配置
    scheduler_timezone: str = "Asia/Shanghai"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_prefix = "DNS_"
        extra = "ignore"  # 忽略额外的环境变量


# 创建全局设置实例
settings = Settings()
