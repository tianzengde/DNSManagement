# 使用官方Python 3.12镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ENV LANG=C.UTF-8
ENV TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # certbot依赖
    certbot \
    # DNS工具
    dnsutils \
    # 其他必要工具
    curl \
    wget \
    git \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install uv && \
    uv sync --frozen

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app

# 创建必要的目录
RUN mkdir -p /app/data/logs \
    /app/data/certificates \
    /etc/letsencrypt \
    /var/lib/letsencrypt \
    /var/log/letsencrypt

# 复制DNS验证脚本
COPY scripts/dns_auth_hook.py /usr/local/bin/dns_auth_hook.py

# 设置目录和文件权限
RUN chmod -R 755 /etc/letsencrypt \
    /var/lib/letsencrypt \
    /var/log/letsencrypt && \
    chmod +x /usr/local/bin/dns_auth_hook.py && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/auth/dashboard-stats || exit 1

# 启动命令
CMD ["uv", "run", "main.py"]
