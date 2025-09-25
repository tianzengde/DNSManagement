"""数据库配置和初始化"""
from tortoise import Tortoise
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def init_database():
    """初始化数据库连接"""
    try:
        await Tortoise.init(
            db_url=settings.database_url,
            modules={'models': ['app.models']}
        )
        await Tortoise.generate_schemas()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_database():
    """关闭数据库连接"""
    await Tortoise.close_connections()
    logger.info("数据库连接已关闭")
