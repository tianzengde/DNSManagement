# 域名管理系统

一个基于 FastAPI、Tortoise ORM 和 SQLite 的多云 DNS 域名管理系统，支持华为云和阿里云域名解析服务。

## 功能特性

### 🔐 用户认证
- 安全的JWT令牌认证
- 密码加密存储
- 会话管理和自动登出
- 密码修改功能

### 📊 系统概览
- 实时统计信息展示
- 服务商状态监控
- 域名和证书统计
- 快速操作入口

### 🌐 多云支持
- 支持华为云、阿里云等主流云服务商
- 统一的API接口管理
- 服务商连接测试和状态监控
- 支持扩展更多云服务商

### 🔧 服务商管理
- 添加、编辑、删除DNS服务商配置
- 连接测试和状态监控
- 服务商配置管理
- 批量操作支持

### 📝 域名管理
- 域名解析记录管理
- 支持多种记录类型（A、AAAA、CNAME、MX、TXT、NS）
- 记录搜索和分页功能
- 批量操作和编辑
- 实时同步服务商数据

### 🔒 证书管理
- Let's Encrypt免费证书申请
- 证书状态监控和自动续期
- 证书文件下载和管理
- 即将过期证书提醒
- 域名筛选和批量操作

### 🔄 DDNS管理
- 动态IP地址自动更新
- 多域名DDNS配置支持
- 自定义更新间隔设置
- 详细的更新日志记录
- 批量更新和状态监控

### 🚀 技术特性
- RESTful API接口
- 响应式Web界面
- 模块化架构设计
- Docker容器化支持
- 完整的操作日志记录

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
- **SSL证书申请**: 支持Let's Encrypt免费证书申请
- **证书状态监控**: 实时监控证书有效期和状态
- **自动续期**: 支持证书自动续期功能
- **证书下载**: 支持证书文件下载（证书、私钥、链证书）
- **域名筛选**: 按域名筛选证书列表
- **即将过期提醒**: 显示即将过期的证书
- **证书操作**: 支持证书检查、续期、删除等操作

### 🔄 DDNS管理
- **动态DNS配置**: 支持动态IP地址更新到DNS记录
- **多域名支持**: 支持多个域名的DDNS配置
- **记录类型支持**: 支持A记录和AAAA记录类型
- **自动更新**: 定时检测IP变化并自动更新DNS记录
- **更新间隔设置**: 可自定义IP检测和更新间隔（最小60秒）
- **批量操作**: 支持批量更新所有DDNS配置
- **状态监控**: 实时显示DDNS配置状态和最后更新时间
- **更新日志**: 详细的更新日志记录，支持分页查看
- **手动更新**: 支持手动触发DDNS更新

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

### 申请SSL证书

1. 访问证书管理页面
2. 点击"添加证书"按钮
3. 填写证书信息：
   - 选择域名
   - 证书类型（Let's Encrypt）
   - 是否自动续期
4. 点击"申请证书"按钮
5. 系统将自动申请并安装证书

### 配置DDNS

1. 访问DDNS设置页面
2. 点击"添加DDNS配置"按钮
3. 填写DDNS配置：
   - 配置名称
   - 选择域名
   - 子域名前缀
   - 记录类型（A/AAAA）
   - 更新间隔（秒）
4. 点击"保存"按钮
5. 系统将自动开始监控IP变化并更新DNS记录

## 项目结构

```
DNSManagement/
├── app/                    # 应用核心代码
│   ├── __init__.py
│   ├── config/            # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py    # 系统设置
│   │   └── certificate_config.py  # 证书配置
│   ├── database.py        # 数据库配置
│   ├── models.py          # 数据模型
│   ├── schemas.py         # Pydantic模型
│   ├── api/               # API路由
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证API
│   │   ├── providers.py   # 服务商API
│   │   ├── domains.py     # 域名API
│   │   ├── certificates.py # 证书API
│   │   └── ddns.py        # DDNS API
│   ├── providers/         # 云服务商集成
│   │   ├── __init__.py
│   │   ├── base.py        # 基础类
│   │   ├── huawei.py      # 华为云集成
│   │   └── aliyun.py      # 阿里云集成
│   └── services/          # 业务服务
│       ├── __init__.py
│       ├── certificate_service.py  # 证书服务
│       ├── scheduler_service.py    # 定时任务服务
│       └── sync_service.py         # 同步服务
├── static/                # 静态文件
│   ├── css/               # 样式文件
│   │   ├── main.css       # 主样式
│   │   ├── dashboard.css  # 仪表板样式
│   │   ├── providers.css  # 服务商样式
│   │   ├── domains.css    # 域名样式
│   │   ├── certificates.css # 证书样式
│   │   └── ddns.css       # DDNS样式
│   ├── js/                # JavaScript文件
│   │   ├── app.js         # 共享工具函数
│   │   ├── dashboard.js   # 仪表板逻辑
│   │   ├── providers.js   # 服务商逻辑
│   │   ├── domains.js     # 域名逻辑
│   │   ├── certificates.js # 证书逻辑
│   │   ├── ddns.js        # DDNS逻辑
│   │   └── components/    # 组件
│   │       ├── modal.js   # 模态框组件
│   │       └── sidebar.js # 侧边栏组件
│   ├── dashboard.html     # 仪表板页面
│   ├── providers.html     # 服务商页面
│   ├── domains.html       # 域名页面
│   ├── certificates.html  # 证书页面
│   ├── ddns.html          # DDNS页面
│   └── login.html         # 登录页面
├── data/                  # 数据目录
│   ├── db/                # 数据库目录
│   │   └── dns_management.db  # SQLite数据库
│   ├── certificates/      # 证书存储目录
│   ├── letsencrypt/       # Let's Encrypt证书目录
│   └── logs/              # 日志目录
├── logs/                  # 日志目录
├── scripts/               # 脚本目录
│   └── dns_auth_hook.py   # DNS认证钩子脚本
├── docker/                # Docker配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── build.sh
├── main.py               # 主应用文件
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

### 证书管理

- `GET /api/certificates/` - 获取证书列表
- `POST /api/certificates/` - 申请新证书
- `GET /api/certificates/{id}` - 获取单个证书
- `PUT /api/certificates/{id}` - 更新证书配置
- `DELETE /api/certificates/{id}` - 删除证书
- `POST /api/certificates/{id}/renew` - 续期证书
- `GET /api/certificates/{id}/download` - 下载证书文件
- `GET /api/certificates/expiring` - 获取即将过期的证书

### DDNS管理

- `GET /api/ddns/` - 获取DDNS配置列表
- `POST /api/ddns/` - 创建DDNS配置
- `GET /api/ddns/{id}` - 获取单个DDNS配置
- `PUT /api/ddns/{id}` - 更新DDNS配置
- `DELETE /api/ddns/{id}` - 删除DDNS配置
- `POST /api/ddns/{id}/update` - 手动更新DDNS记录
- `GET /api/ddns/{id}/logs` - 获取DDNS更新日志（支持分页）

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
