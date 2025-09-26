# 域名管理系统

一个基于 FastAPI、Tortoise ORM 和 SQLite 的多云 DNS 域名管理系统，支持华为云和阿里云域名解析服务。

## 功能特性

- 🔐 **用户认证**: 安全的用户登录和密码管理
- 📊 **系统概览**: 直观的仪表板显示系统统计信息
- 🌐 **多云支持**: 支持华为云、阿里云等主流云服务商
- 📊 **Web管理界面**: 直观的Web界面管理服务商和域名
- 🔧 **服务商管理**: 添加、编辑、删除DNS服务商配置
- 📝 **域名管理**: 管理域名解析记录
- 🔄 **自动同步**: 支持域名解析记录自动同步
- 📋 **操作日志**: 记录所有操作和同步状态
- 🚀 **RESTful API**: 完整的API接口支持

## 技术栈

- **后端**: FastAPI + Tortoise ORM
- **数据库**: SQLite
- **前端**: HTML + CSS + JavaScript
- **云服务商**: 华为云、阿里云

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 启动应用

```bash
uv run main.py
```

### 3. 访问系统

打开浏览器访问 `http://localhost:8000`，系统会自动跳转到登录页面。

**默认登录信息：**
- 用户名：`admin`
- 密码：`admin123`

> ⚠️ **安全提示**: 首次登录后请立即修改默认密码！

## 系统功能

### 🔐 用户认证
- 安全的JWT令牌认证
- 密码加密存储
- 会话管理
- 密码修改功能

### 📊 系统概览
- 服务商统计（总数、启用数）
- 域名统计
- 证书统计（总数、有效数、即将过期数）
- 快速操作入口

### 🔧 服务商管理
- 支持华为云、阿里云
- 连接测试和状态监控
- 批量同步域名
- 服务商配置管理

### 🌐 域名管理
- 域名解析记录管理
- 支持多种记录类型（A、AAAA、CNAME、MX、TXT、NS）
- 批量操作
- 记录搜索和分页

### 🔒 证书管理
- SSL证书申请和管理
- 自动续期
- 证书状态监控
- 证书下载

### 3. 访问系统

- 管理界面: http://localhost:8000
- API文档: http://localhost:8000/docs
- 服务商管理: http://localhost:8000/providers
- 域名管理: http://localhost:8000/domains

## 使用说明

### 添加服务商

1. 访问服务商管理页面
2. 点击"添加服务商"按钮
3. 填写服务商信息：
   - 服务商名称
   - 服务商类型（华为云/阿里云）
   - 访问密钥
   - 秘密密钥
   - 区域
4. 点击"保存"按钮

### 添加域名

1. 访问域名管理页面
2. 点击"添加域名"按钮
3. 填写域名信息：
   - 域名
   - 选择服务商
   - 是否启用
   - 是否自动更新
4. 点击"保存"按钮

## 项目结构

```
CertManagement/
├── app/                    # 应用核心代码
│   ├── __init__.py
│   ├── config.py          # 配置文件
│   ├── database.py        # 数据库配置
│   ├── models.py          # 数据模型
│   ├── schemas.py         # Pydantic模型
│   ├── api/               # API路由
│   │   ├── __init__.py
│   │   ├── providers.py   # 服务商API
│   │   └── domains.py     # 域名API
│   └── providers/         # 云服务商集成
│       ├── __init__.py
│       ├── base.py        # 基础类
│       ├── huawei.py      # 华为云集成
│       └── aliyun.py      # 阿里云集成
├── static/                # 静态文件
│   └── index.html         # 前端页面
├── data/                  # 数据目录
│   └── dns_management.db  # SQLite数据库
├── logs/                  # 日志目录
├── main.py               # 主应用文件
├── test/                 # 测试目录
│   ├── __init__.py
│   ├── test_database.py  # 数据库测试
│   ├── test_api.py       # API测试
│   └── demo.py           # 演示脚本
├── pyproject.toml        # 项目配置
└── README.md             # 说明文档
```

## API接口

### 服务商管理

- `GET /api/providers/` - 获取服务商列表
- `POST /api/providers/` - 创建服务商
- `GET /api/providers/{id}` - 获取单个服务商
- `PUT /api/providers/{id}` - 更新服务商
- `DELETE /api/providers/{id}` - 删除服务商
- `POST /api/providers/{id}/test` - 测试服务商连接

### 域名管理

- `GET /api/domains/` - 获取域名列表
- `POST /api/domains/` - 创建域名
- `GET /api/domains/{id}` - 获取单个域名
- `PUT /api/domains/{id}` - 更新域名
- `DELETE /api/domains/{id}` - 删除域名
- `GET /api/domains/{id}/records` - 获取域名解析记录
- `POST /api/domains/{id}/records` - 添加解析记录
- `PUT /api/domains/records/{id}` - 更新解析记录
- `DELETE /api/domains/records/{id}` - 删除解析记录

## 配置说明

系统配置通过 `app/config.py` 文件管理，主要配置项：

- `database_url`: 数据库连接字符串
- `host`: 服务器监听地址
- `port`: 服务器端口
- `debug`: 调试模式
- `log_level`: 日志级别

## 测试

### 运行测试

```bash
# 测试数据库
uv run python test/test_database.py

# 测试API（需要应用运行）
uv run python test/test_api.py

# 运行演示
uv run python test/demo.py
```

### 测试说明

- `test_database.py`: 测试数据库连接和模型操作
- `test_api.py`: 测试API接口（需要应用运行）
- `demo.py`: 完整的功能演示脚本

## 开发说明

### 添加新的云服务商

1. 在 `app/providers/` 目录下创建新的服务商文件
2. 继承 `BaseProvider` 类并实现所有抽象方法
3. 在 `app/providers/__init__.py` 中导入新服务商
4. 在 `app/models.py` 中添加新的服务商类型枚举
5. 更新API路由以支持新服务商

### 数据库迁移

系统使用 Tortoise ORM 的自动迁移功能，首次运行时会自动创建数据库表结构。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
