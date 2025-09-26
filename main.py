"""主应用入口"""
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_database, close_database
from app.api import providers, domains, certificates, auth, ddns
from app.services.scheduler_service import scheduler_service

# 配置日志
# 确保日志目录存在
log_path = Path(settings.log_file)
log_path.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在启动应用...")
    await init_database()
    
    # 初始化默认用户
    await auth.init_default_user()
    
    # 启动定时任务调度器
    scheduler_service.start()
    logger.info("定时任务调度器已启动")
    
    # 初始化DDNS调度服务
    await scheduler_service.initialize_ddns()
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("正在关闭应用...")
    
    # 停止定时任务调度器
    scheduler_service.stop()
    logger.info("定时任务调度器已停止")
    
    await close_database()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="多云DNS域名管理系统",
    lifespan=lifespan
)

# 注册API路由
app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(domains.router)
app.include_router(certificates.router)
app.include_router(ddns.router)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页 - 重定向到服务商管理页面"""
    with open("static/providers.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    with open("static/login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """仪表板页面"""
    with open("static/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()




@app.get("/providers", response_class=HTMLResponse)
async def providers_page():
    """服务商管理页面"""
    with open("static/providers.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/domains", response_class=HTMLResponse)
async def domains_page():
    """域名管理页面"""
    with open("static/domains.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/certificates", response_class=HTMLResponse)
async def certificates_page():
    """证书管理页面"""
    with open("static/certificates.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/ddns", response_class=HTMLResponse)
async def ddns_page():
    """DDNS设置页面"""
    with open("static/ddns.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
