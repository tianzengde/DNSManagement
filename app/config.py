"""应用配置模块"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "域名管理系统"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 数据库配置 - 使用相对路径存储到data目录
    database_url: str = "sqlite://./data/dns_management.db"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 安全配置
    secret_key: str = "your-secret-key-change-in-production"
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # 确保data和logs目录存在
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
