"""用户认证API"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import logging
import hashlib

from app.models import User
from app.schemas import UserLogin, UserPasswordChange, UserResponse, LoginResponse, DashboardStats
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

logger = logging.getLogger(__name__)

# JWT配置
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30天


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await User.get_or_none(username=username)
    if user is None:
        raise credentials_exception
    
    return user


async def init_default_user():
    """初始化默认用户"""
    try:
        # 检查是否已存在admin用户
        admin_user = await User.get_or_none(username="admin")
        if not admin_user:
            # 创建默认admin用户
            admin_user = await User.create(
                username="admin",
                password_hash=get_password_hash("admin123"),
                is_active=True
            )
            logger.info("默认admin用户创建成功")
        else:
            logger.info("admin用户已存在")
    except Exception as e:
        logger.error(f"初始化默认用户失败: {e}")
        # 即使失败也不抛出异常，避免影响应用启动


@router.post("/login", response_model=LoginResponse)
async def login(user_login: UserLogin):
    """用户登录"""
    # 验证用户名和密码
    user = await User.get_or_none(username=user_login.username)
    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.from_orm(current_user)


@router.put("/change-password")
async def change_password(
    password_change: UserPasswordChange,
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_change.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    current_user.password_hash = get_password_hash(password_change.new_password)
    await current_user.save()
    
    return {"message": "密码修改成功"}


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """获取首页统计数据"""
    from app.models import Provider, Domain, Certificate, CertificateStatus, DDNSConfig
    
    # 统计服务商
    total_providers = await Provider.all().count()
    enabled_providers = await Provider.filter(enabled=True).count()
    
    # 统计域名
    total_domains = await Domain.all().count()
    
    # 统计证书
    total_certificates = await Certificate.all().count()
    valid_certificates = await Certificate.filter(status=CertificateStatus.VALID).count()
    
    # 统计即将过期的证书（30天内）
    from datetime import datetime, timedelta
    thirty_days_later = datetime.now() + timedelta(days=30)
    expiring_certificates = await Certificate.filter(
        status=CertificateStatus.VALID,
        not_after__lte=thirty_days_later
    ).count()
    
    # 统计DDNS配置
    total_ddns_configs = await DDNSConfig.all().count()
    active_ddns_configs = await DDNSConfig.filter(enabled=True).count()
    
    return DashboardStats(
        total_providers=total_providers,
        enabled_providers=enabled_providers,
        total_domains=total_domains,
        total_certificates=total_certificates,
        valid_certificates=valid_certificates,
        expiring_certificates=expiring_certificates,
        total_ddns_configs=total_ddns_configs,
        active_ddns_configs=active_ddns_configs
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    # JWT是无状态的，这里只是返回成功消息
    # 实际的登出逻辑在前端删除token
    return {"message": "登出成功"}
