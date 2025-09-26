# 构建阶段
FROM python:3.12-alpine AS builder

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apk add --no-cache \
    build-base \
    curl \
    linux-headers

# 安装uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件（利用Docker缓存层）
COPY pyproject.toml uv.lock README.md ./

# 安装Python依赖到虚拟环境
RUN uv sync --frozen

# 生产阶段
FROM python:3.12-alpine AS production

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8

# 安装运行时依赖（最小化）
RUN apk add --no-cache \
    certbot \
    bind-tools \
    curl \
    ca-certificates \
    openssl

# 安装uv
RUN pip install uv

# 创建非root用户
RUN addgroup -g 1000 app && adduser -D -u 1000 -G app app

# 创建用户主目录和缓存目录
RUN mkdir -p /home/app/.cache/uv && chown -R app:app /home/app

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码（只复制必要的文件）
COPY --chown=app:app app/ ./app/
COPY --chown=app:app scripts/ ./scripts/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app main.py ./

# 创建必要的目录
RUN mkdir -p /app/data/logs \
    /app/data/certificates \
    /etc/letsencrypt \
    /var/lib/letsencrypt \
    /var/log/letsencrypt

# 复制DNS验证脚本
COPY --chown=app:app scripts/dns_auth_hook.py /usr/local/bin/dns_auth_hook.py

# 设置目录和文件权限
RUN chmod -R 755 /etc/letsencrypt \
    /var/lib/letsencrypt \
    /var/log/letsencrypt && \
    chmod +x /usr/local/bin/dns_auth_hook.py && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 启动命令
CMD ["uv", "run", "main.py"]