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
    log_file: str = "data/logs/app.log"
    
    # 数据库配置
    database_url: str = "sqlite://./data/db/dns_management.db"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 安全配置
    jwt_secret_key: str = "your-jwt-secret-key-here"
    
    # 定时任务配置
    scheduler_timezone: str = "Asia/Shanghai"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的目录"""
        # 确定基础路径
        if os.path.exists("/app"):
            # Docker环境
            base_path = "/app/data"
        else:
            # 开发环境
            base_path = "data"
        
        # 创建目录
        directories = [
            f"{base_path}/logs",
            f"{base_path}/db", 
            f"{base_path}/certificates/certbot_config"
        ]
        
        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                print(f"成功创建目录: {directory}")
            except PermissionError as e:
                print(f"警告: 无法创建目录 {directory}: {e}")
                # 继续执行，不中断应用启动
                # 在Docker环境中，volume挂载可能会覆盖权限
                # 这种情况下，目录可能已经存在但权限不正确
    
    class Config:
        env_file = ".env"
        env_prefix = "DNS_"
        extra = "ignore"  # 忽略额外的环境变量


# 创建全局设置实例
settings = Settings()
