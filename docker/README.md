# Docker镜像构建脚本使用说明

## 功能特性

- ✅ 自动版本号递增
- ✅ 多种构建选项（Alpine/Slim基础镜像）
- ✅ 镜像清理功能
- ✅ 自动推送到仓库
- ✅ 彩色日志输出
- ✅ 错误处理和验证
- ✅ 测试版本和生产版本分离管理
- ✅ 独立版本文件管理

## 使用方法

### 基本用法

```bash
# 显示帮助信息
./docker/build.sh --help

# 自动递增版本号，构建Alpine最小化镜像
./docker/build.sh --auto --minimal

# 指定版本号构建
./docker/build.sh --version 1.2.3

# 构建并推送到仓库
./docker/build.sh --auto --push

# 构建测试版本
./docker/build.sh --auto --test

# 构建指定版本的测试版本
./docker/build.sh --version 1.2.3 --test
```

### 常用命令

```bash
# 1. 开发环境快速构建（生产版本）
./docker/build.sh --auto --minimal

# 2. 开发环境快速构建（测试版本）
./docker/build.sh --auto --test --minimal

# 3. 生产环境构建并推送
./docker/build.sh --version 1.0.0 --tag stable --push

# 4. 测试环境构建并推送
./docker/build.sh --version 1.0.0 --test --push

# 5. 清理旧镜像后构建
./docker/build.sh --auto --clean --minimal

# 6. 不使用缓存构建
./docker/build.sh --auto --no-cache --minimal
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `-h, --help` | 显示帮助信息 | `./build.sh --help` |
| `-v, --version` | 指定版本号 | `--version 1.2.3` |
| `-a, --auto` | 自动递增版本号 | `--auto` |
| `-t, --tag` | 指定标签 | `--tag stable` |
| `--test` | 构建测试版本 | `--test` |
| `-p, --push` | 构建后推送 | `--push` |
| `-c, --clean` | 构建前清理 | `--clean` |
| `-b, --base` | 使用Slim镜像 | `--base` |
| `-m, --minimal` | 使用Alpine镜像 | `--minimal` |
| `--no-cache` | 不使用缓存 | `--no-cache` |

## 版本号管理

### 版本文件分离
- **生产版本**：使用 `docker/version.txt` 文件
- **测试版本**：使用 `docker/version-test.txt` 文件
- 两个版本文件独立管理，互不影响

### 版本号规则
- 版本号格式：`x.y.z`（例如：1.2.3）
- 测试版本会自动添加 `-test` 后缀（例如：1.2.3-test）
- 自动递增会递增补丁版本号（z）
- 手动指定版本号会覆盖当前版本

### 版本文件示例
```bash
# 生产版本文件 (docker/version.txt)
1.0.2

# 测试版本文件 (docker/version-test.txt)
0.0.1
```

## 构建的镜像标签

### 生产版本
脚本会同时创建两个标签：
- `tian/dnsmanagement:latest`（或指定的标签）
- `tian/dnsmanagement:1.2.3`（版本号标签）

### 测试版本
脚本会同时创建两个标签：
- `tian/dnsmanagement:latest-test`（或指定的标签-test）
- `tian/dnsmanagement:1.2.3-test`（版本号-test标签）

## 示例工作流

### 开发环境
```bash
# 快速构建测试（生产版本）
./docker/build.sh --auto --minimal

# 快速构建测试（测试版本）
./docker/build.sh --auto --test --minimal
```

### 生产环境
```bash
# 1. 清理旧镜像
./docker/build.sh --clean

# 2. 构建新版本
./docker/build.sh --version 1.0.0 --tag stable

# 3. 推送到仓库
./docker/build.sh --version 1.0.0 --tag stable --push
```

### 测试环境
```bash
# 1. 清理旧镜像
./docker/build.sh --clean

# 2. 构建测试版本
./docker/build.sh --version 1.0.0 --test

# 3. 推送测试版本到仓库
./docker/build.sh --version 1.0.0 --test --push
```

### CI/CD集成
```bash
# 生产环境CI/CD
./docker/build.sh --auto --minimal --push

# 测试环境CI/CD
./docker/build.sh --auto --test --minimal --push
```

## 注意事项

1. 确保Docker服务正在运行
2. 确保有足够的磁盘空间
3. 推送功能需要先登录Docker仓库
4. 版本号文件会自动创建和管理
5. 脚本会自动验证版本号格式
6. 测试版本和生产版本使用独立的版本文件
7. 测试版本会自动添加 `-test` 后缀到版本号和标签

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x docker/build.sh
   ```

2. **Docker未运行**
   ```bash
   sudo systemctl start docker
   ```

3. **版本号格式错误**
   - 确保版本号格式为 `x.y.z`
   - 例如：`1.0.0`、`2.1.3`

4. **推送失败**
   - 确保已登录Docker仓库
   - 检查网络连接
   - 验证仓库权限
