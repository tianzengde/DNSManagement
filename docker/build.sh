#!/bin/bash

# DNS管理应用Docker镜像构建脚本
# 支持版本号自增和多种构建选项

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="tian/dnsmanagement"
DOCKERFILE_PATH="docker/Dockerfile"
VERSION_FILE="docker/version.txt"
VERSION_TEST_FILE="docker/version-test.txt"

# 显示帮助信息
show_help() {
    echo -e "${BLUE}DNS管理应用Docker镜像构建脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -v, --version VERSION   指定版本号 (例如: 1.0.0)"
    echo "  -a, --auto              自动递增版本号"
    echo "  -t, --tag TAG           指定标签 (默认: latest)"
    echo "  --test                  构建测试版本镜像 (添加-test后缀)"
    echo "  -p, --push              构建后推送到仓库"
    echo "  -c, --clean             构建前清理旧镜像"
    echo "  -b, --base              使用基础镜像 (python:3.12-slim)"
    echo "  -m, --minimal           使用最小化镜像 (python:3.12-alpine)"
    echo "  --no-cache              不使用Docker缓存"
    echo ""
    echo "示例:"
    echo "  $0 --auto --minimal     自动递增版本号，构建Alpine最小化镜像"
    echo "  $0 -v 1.2.3 -t stable   构建指定版本号的稳定版本"
    echo "  $0 --auto --test        自动递增版本号，构建测试版本"
    echo "  $0 -v 1.2.3 --test      构建指定版本号的测试版本"
    echo "  $0 --auto --push        自动递增版本号并推送到仓库"
    echo ""
    echo "版本管理:"
    echo "  - 生产版本使用: docker/version.txt"
    echo "  - 测试版本使用: docker/version-test.txt"
    echo "  - 两个版本文件独立管理，互不影响"
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker未运行或无法访问"
        exit 1
    fi
}

# 获取当前版本号
get_current_version() {
    local version_file=$1
    if [ -f "$version_file" ]; then
        cat "$version_file"
    else
        echo "0.0.0"
    fi
}

# 保存版本号
save_version() {
    local version=$1
    local version_file=$2
    echo "$version" > "$version_file"
}

# 递增版本号
increment_version() {
    local version=$1
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    local patch=$(echo $version | cut -d. -f3)
    
    patch=$((patch + 1))
    echo "$major.$minor.$patch"
}

# 验证版本号格式
validate_version() {
    local version=$1
    if [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# 清理旧镜像
clean_images() {
    log_info "清理旧镜像..."
    docker images "$PROJECT_NAME" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | tail -n +2 | while read line; do
        if [ ! -z "$line" ]; then
            local image=$(echo $line | awk '{print $1}')
            log_info "删除镜像: $image"
            docker rmi "$image" 2>/dev/null || true
        fi
    done
}

# 构建镜像
build_image() {
    local version=$1
    local tag=$2
    local base_image=$3
    local no_cache=$4
    
    local image_tag="$PROJECT_NAME:$tag"
    local version_tag="$PROJECT_NAME:$version"
    
    log_info "开始构建镜像..."
    log_info "项目: $PROJECT_NAME"
    log_info "版本: $version"
    log_info "标签: $tag"
    log_info "基础镜像: $base_image"
    
    # 检查是否为测试版本
    if [[ "$version" == *"-test" ]] || [[ "$tag" == *"-test" ]]; then
        log_info "构建类型: 测试版本"
    else
        log_info "构建类型: 生产版本"
    fi
    
    # 构建命令
    local build_cmd="docker build"
    
    if [ "$no_cache" = true ]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    build_cmd="$build_cmd -t $image_tag -t $version_tag"
    build_cmd="$build_cmd -f $DOCKERFILE_PATH"
    build_cmd="$build_cmd --build-arg BASE_IMAGE=$base_image"
    build_cmd="$build_cmd ."
    
    log_info "执行命令: $build_cmd"
    
    if eval $build_cmd; then
        log_success "镜像构建成功!"
        log_success "镜像标签: $image_tag"
        log_success "版本标签: $version_tag"
        
        # 显示镜像信息
        docker images "$PROJECT_NAME" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -3
    else
        log_error "镜像构建失败!"
        exit 1
    fi
}

# 推送镜像
push_image() {
    local version=$1
    local tag=$2
    
    local image_tag="$PROJECT_NAME:$tag"
    local version_tag="$PROJECT_NAME:$version"
    
    log_info "推送镜像到仓库..."
    
    if docker push "$image_tag" && docker push "$version_tag"; then
        log_success "镜像推送成功!"
    else
        log_error "镜像推送失败!"
        exit 1
    fi
}

# 主函数
main() {
    local version=""
    local tag="latest"
    local auto_increment=false
    local push=false
    local clean=false
    local base_image="python:3.12-alpine"
    local no_cache=false
    local test_mode=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                version="$2"
                shift 2
                ;;
            -a|--auto)
                auto_increment=true
                shift
                ;;
            -t|--tag)
                tag="$2"
                shift 2
                ;;
            -p|--push)
                push=true
                shift
                ;;
            -c|--clean)
                clean=true
                shift
                ;;
            -b|--base)
                base_image="python:3.12-slim"
                shift
                ;;
            -m|--minimal)
                base_image="python:3.12-alpine"
                shift
                ;;
            --no-cache)
                no_cache=true
                shift
                ;;
            --test)
                test_mode=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查Docker
    check_docker
    
    # 根据测试模式选择版本文件
    local version_file
    if [ "$test_mode" = true ]; then
        version_file="$VERSION_TEST_FILE"
        log_info "使用测试版本文件: $version_file"
    else
        version_file="$VERSION_FILE"
        log_info "使用生产版本文件: $version_file"
    fi
    
    # 处理版本号
    if [ "$auto_increment" = true ]; then
        local current_version=$(get_current_version "$version_file")
        version=$(increment_version $current_version)
        log_info "自动递增版本号: $current_version -> $version"
        save_version "$version" "$version_file"
    elif [ -z "$version" ]; then
        version=$(get_current_version "$version_file")
        log_info "使用当前版本号: $version"
    else
        # 保存原始版本号（不包含test后缀）
        local original_version="$version"
        if ! validate_version "$original_version"; then
            log_error "版本号格式错误: $original_version (应为 x.y.z 格式)"
            exit 1
        fi
        save_version "$original_version" "$version_file"
    fi
    
    # 如果是测试模式，添加测试标识
    if [ "$test_mode" = true ]; then
        version="${version}-test"
        log_info "测试模式: 版本号添加-test后缀 -> $version"
    fi
    
    # 清理旧镜像
    if [ "$clean" = true ]; then
        clean_images
    fi
    
    # 如果是测试模式，修改标签
    if [ "$test_mode" = true ]; then
        tag="${tag}-test"
        log_info "测试模式: 标签添加-test后缀 -> $tag"
    fi
    
    # 构建镜像
    build_image "$version" "$tag" "$base_image" "$no_cache"
    
    # 推送镜像
    if [ "$push" = true ]; then
        push_image "$version" "$tag"
    fi
    
    # 显示构建完成信息
    if [ "$test_mode" = true ]; then
        log_success "测试版本构建完成! 版本: $version, 标签: $tag"
    else
        log_success "生产版本构建完成! 版本: $version, 标签: $tag"
    fi
}

# 运行主函数
main "$@"
