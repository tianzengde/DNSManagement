/**
 * 系统概览页面管理器
 */
class Dashboard {
    constructor() {
        this.init();
    }
    
    init() {
        this.checkAuth();
        this.bindEvents();
        this.loadDashboardData();
    }
    
    checkAuth() {
        const token = localStorage.getItem('access_token');
        const userInfo = localStorage.getItem('user_info');
        
        if (!token || !userInfo) {
            window.location.href = '/login';
            return;
        }
        
        try {
            const user = JSON.parse(userInfo);
            const userNameElement = document.getElementById('userName');
            if (userNameElement) {
                userNameElement.textContent = `欢迎，${user.username}`;
            }
        } catch (e) {
            console.error('解析用户信息失败:', e);
            this.logout();
        }
    }
    
    bindEvents() {
        const passwordChangeForm = document.getElementById('passwordChangeForm');
        if (passwordChangeForm) {
            passwordChangeForm.addEventListener('submit', (e) => {
                this.handlePasswordChange(e);
            });
        }
    }
    
    async loadDashboardData() {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/auth/dashboard', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const stats = await response.json();
                this.renderStats(stats);
            } else if (response.status === 401) {
                this.logout();
            } else {
                this.showError('加载统计数据失败');
            }
        } catch (error) {
            this.showError('网络错误，请检查连接');
        }
    }
    
    renderStats(stats) {
        const container = document.getElementById('statsContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-card-header">
                    <div class="stat-icon providers">🔧</div>
                    <div>
                        <h3 class="stat-title">服务商总数</h3>
                    </div>
                </div>
                <p class="stat-value">${stats.total_providers}</p>
                <p class="stat-description">已启用: ${stats.enabled_providers}</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-card-header">
                    <div class="stat-icon domains">🌐</div>
                    <div>
                        <h3 class="stat-title">域名总数</h3>
                    </div>
                </div>
                <p class="stat-value">${stats.total_domains}</p>
                <p class="stat-description">管理的域名数量</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-card-header">
                    <div class="stat-icon certificates">🔒</div>
                    <div>
                        <h3 class="stat-title">证书总数</h3>
                    </div>
                </div>
                <p class="stat-value">${stats.total_certificates}</p>
                <p class="stat-description">有效证书: ${stats.valid_certificates}</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-card-header">
                    <div class="stat-icon expiring">⚠️</div>
                    <div>
                        <h3 class="stat-title">即将过期</h3>
                    </div>
                </div>
                <p class="stat-value">${stats.expiring_certificates}</p>
                <p class="stat-description">30天内过期的证书</p>
            </div>
            
            <div class="stat-card">
                <div class="stat-card-header">
                    <div class="stat-icon ddns">🔄</div>
                    <div>
                        <h3 class="stat-title">DDNS配置</h3>
                    </div>
                </div>
                <p class="stat-value">${stats.total_ddns_configs}</p>
                <p class="stat-description">活跃配置: ${stats.active_ddns_configs}</p>
            </div>
        `;
    }
    
    showPasswordChangeModal() {
        const modal = document.getElementById('passwordChangeModal');
        if (modal) {
            modal.style.display = 'block';
        }
    }
    
    hidePasswordChangeModal() {
        const modal = document.getElementById('passwordChangeModal');
        const form = document.getElementById('passwordChangeForm');
        if (modal) {
            modal.style.display = 'none';
        }
        if (form) {
            form.reset();
        }
    }
    
    async handlePasswordChange(e) {
        e.preventDefault();
        
        const oldPassword = document.getElementById('oldPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (newPassword !== confirmPassword) {
            alert('新密码和确认密码不匹配');
            return;
        }
        
        if (newPassword.length < 6) {
            alert('新密码长度至少6位');
            return;
        }
        
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = '修改中...';
        }
        
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/auth/change-password', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword
                })
            });
            
            if (response.ok) {
                alert('密码修改成功');
                this.hidePasswordChangeModal();
            } else {
                const error = await response.json();
                alert(error.detail || '密码修改失败');
            }
        } catch (error) {
            alert('网络错误，请检查连接');
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = '修改密码';
            }
        }
    }
    
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login';
    }
    
    navigateTo(path) {
        window.location.href = path;
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 3000);
        }
    }
}

// 检查认证状态
function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// 切换侧边栏显示/隐藏
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// 导出 Dashboard 类
window.Dashboard = Dashboard;

// 初始化仪表板
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;
    
    // 初始化仪表板
    window.dashboard = new Dashboard();
    
    // 创建侧边栏
    const sidebar = new Sidebar();
    
    // 延迟设置仪表板为当前活跃页面，确保侧边栏已创建
    setTimeout(() => {
        const dashboardNavItem = document.querySelector('[href="/dashboard"]');
        if (dashboardNavItem) {
            // 清除其他活跃状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            // 设置当前页面为活跃
            dashboardNavItem.classList.add('active');
        }
    }, 100);
});
