"""定时任务调度服务"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.sync_service import DomainSyncService

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.sync_service = DomainSyncService()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """设置定时任务"""
        # 每15分钟同步一次域名
        self.scheduler.add_job(
            func=self.sync_domains_job,
            trigger=IntervalTrigger(minutes=15),
            id='sync_domains',
            name='同步域名任务',
            replace_existing=True
        )
        
        # 每小时检查一次证书状态
        self.scheduler.add_job(
            func=self.check_certificates_job,
            trigger=IntervalTrigger(hours=1),
            id='check_certificates',
            name='检查证书状态任务',
            replace_existing=True
        )
        
        logger.info("定时任务设置完成")
    
    async def sync_domains_job(self):
        """同步域名任务"""
        logger.info("开始执行域名同步任务")
        try:
            await self.sync_service.sync_all_providers()
            logger.info("域名同步任务执行完成")
        except Exception as e:
            logger.error(f"域名同步任务执行失败: {e}")
    
    async def check_certificates_job(self):
        """检查证书状态任务"""
        logger.info("开始执行证书状态检查任务")
        try:
            # 这里可以添加证书状态检查逻辑
            # 暂时只是记录日志
            logger.info("证书状态检查任务执行完成")
        except Exception as e:
            logger.error(f"证书状态检查任务执行失败: {e}")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")
    
    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()
    
    def add_manual_sync_job(self, provider_id: int):
        """添加手动同步任务"""
        job_id = f'manual_sync_{provider_id}'
        self.scheduler.add_job(
            func=self.manual_sync_job,
            args=[provider_id],
            id=job_id,
            name=f'手动同步服务商{provider_id}',
            replace_existing=True
        )
        logger.info(f"添加手动同步任务: 服务商{provider_id}")
    
    async def manual_sync_job(self, provider_id: int):
        """手动同步任务"""
        logger.info(f"开始执行手动同步任务: 服务商{provider_id}")
        try:
            await self.sync_service.sync_single_provider(provider_id)
            logger.info(f"手动同步任务执行完成: 服务商{provider_id}")
        except Exception as e:
            logger.error(f"手动同步任务执行失败: 服务商{provider_id}, 错误: {e}")


# 全局调度器实例
scheduler_service = SchedulerService()
