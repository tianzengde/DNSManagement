"""
DDNS更新服务
"""
import asyncio
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.models import DDNSConfig

logger = logging.getLogger(__name__)

class DDNSUpdateService:
    """DDNS更新服务"""
    
    def __init__(self, scheduler: AsyncIOScheduler):
        """初始化DDNS更新服务"""
        self.scheduler = scheduler
        logger.info("DDNS更新服务已初始化")
    
    async def load_ddns_jobs(self):
        """加载所有启用的DDNS配置并添加到调度器"""
        try:
            # 获取所有启用且为自动更新的DDNS配置
            configs = await DDNSConfig.filter(
                enabled=True, 
                update_method="auto"
            ).prefetch_related('domain__provider')
            
            logger.info(f"找到 {len(configs)} 个启用的DDNS配置")
            
            for config in configs:
                await self.add_ddns_job(config)
                
            logger.info("DDNS定时任务加载完成")
            
        except Exception as e:
            logger.error(f"加载DDNS定时任务失败: {str(e)}")
    
    async def add_ddns_job(self, config: DDNSConfig):
        """添加DDNS更新任务到调度器"""
        try:
            job_id = f"ddns_update_{config.id}"
            
            # 检查任务是否已存在
            if self.scheduler.get_job(job_id):
                logger.info(f"DDNS任务已存在，跳过: {config.name}")
                return
            
            # 添加定时任务
            self.scheduler.add_job(
                func=self._ddns_update_job,
                trigger='interval',
                seconds=config.update_interval,
                id=job_id,
                args=[config.id],
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60
            )
            
            logger.info(f"添加DDNS定时任务: {config.name} (间隔: {config.update_interval}秒)")
            
        except Exception as e:
            logger.error(f"添加DDNS定时任务失败: {str(e)}")
    
    def remove_ddns_job(self, config_id: str):
        """从调度器中删除DDNS任务"""
        try:
            job_id = f"ddns_update_{config_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"删除DDNS定时任务: {config_id}")
            else:
                logger.warning(f"未找到DDNS定时任务: {config_id}")
                
        except Exception as e:
            logger.error(f"删除DDNS定时任务失败: {str(e)}")
    
    async def _ddns_update_job(self, config_id: str):
        """DDNS更新任务执行函数"""
        try:
            logger.info(f"开始执行DDNS更新任务: {config_id}")
            
            # 动态导入以避免循环导入
            from app.api.ddns import update_ddns_record
            
            # 执行DDNS更新
            result = await update_ddns_record(config_id, force=False)
            
            if result.success:
                logger.info(f"DDNS更新成功: {config_id} - {result.message}")
            else:
                logger.warning(f"DDNS更新失败: {config_id} - {result.message}")
                
        except Exception as e:
            logger.error(f"执行DDNS更新任务失败: {config_id} - {str(e)}")
    
    def get_job_status(self, config_id: str) -> Optional[dict]:
        """获取DDNS任务状态"""
        try:
            job_id = f"ddns_update_{config_id}"
            job = self.scheduler.get_job(job_id)
            
            if job:
                return {
                    "id": job.id,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                    "pending": job.pending
                }
            return None
            
        except Exception as e:
            logger.error(f"获取DDNS任务状态失败: {str(e)}")
            return None
    
    def list_all_jobs(self) -> list:
        """列出所有DDNS任务"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                if job.id.startswith("ddns_update_"):
                    jobs.append({
                        "id": job.id,
                        "config_id": job.id.replace("ddns_update_", ""),
                        "next_run_time": job.next_run_time,
                        "trigger": str(job.trigger),
                        "pending": job.pending
                    })
            return jobs
            
        except Exception as e:
            logger.error(f"列出DDNS任务失败: {str(e)}")
            return []
