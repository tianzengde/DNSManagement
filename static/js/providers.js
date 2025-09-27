/**
 * 服务商管理页面管理器
 */
class ProvidersManager {
    constructor() {
        this.currentProviderId = null;
        this.init();
    }

    init() {
        this.createModals();
        this.bindEvents();
        this.loadProviders();
    }

    createModals() {
        // 创建服务商模态框
        if (!document.getElementById('providerModal')) {
            this.providerModal = ModalUtils.createProviderModal();
        }
    }

    bindEvents() {
        // 模态框关闭
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                this.closeModal(e.target.closest('.modal'));
            });
        });

        // 点击模态框外部关闭
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });

        // 延迟绑定表单提交事件
        setTimeout(() => {
            const providerForm = document.getElementById('providerForm');
            if (providerForm && !providerForm.dataset.bound) {
                providerForm.addEventListener('submit', (e) => {
                    this.handleProviderSubmit(e);
                });
                providerForm.dataset.bound = 'true'; // 标记已绑定，防止重复绑定
            }
        }, 100);
    }

    async loadProviders() {
        try {
            const response = await fetch('/api/providers/');
            const providers = await response.json();
            this.renderProviders(providers);
        } catch (error) {
            this.showAlert('providers-alert', '加载服务商列表失败: ' + error.message, 'error');
        }
    }

    renderProviders(providers) {
        const tbody = document.getElementById('providers-table');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        providers.forEach(provider => {
            const row = document.createElement('tr');
            const statusClass = provider.enabled ? 'enabled' : 'disabled';
            const statusText = provider.enabled ? '启用' : '禁用';
            const lastTest = provider.last_test_at ? 
                new Date(provider.last_test_at).toLocaleString() : '从未测试';

            // 获取类型显示名称
            const typeMapping = {
                1: '华为云',
                2: '阿里云'
            };
            const typeDisplayName = typeMapping[provider.type] || '未知';
            
            // 获取连接状态
            const connectionStatus = provider.status;
            const isConnected = connectionStatus === 'connected';
            const connectionText = isConnected ? '已连接' : 
                                 connectionStatus === 'failed' ? '连接失败' :
                                 connectionStatus === 'error' ? '连接错误' : '未测试';
            const connectionClass = isConnected ? 'enabled' : 'disabled';

            row.innerHTML = `
                <td style="text-align: center; vertical-align: middle;">${provider.name}</td>
                <td style="text-align: center; vertical-align: middle;">${typeDisplayName}</td>
                <td style="text-align: center; vertical-align: middle;">
                    <label class="switch">
                        <input type="checkbox" ${provider.enabled ? 'checked' : ''} 
                               onchange="providersApp.updateProviderStatus(${provider.id}, this.checked, this)">
                        <span class="slider"></span>
                    </label>
                </td>
                <td style="text-align: center; vertical-align: middle;">
                    <span class="status ${connectionClass}">${connectionText}</span>
                </td>
                <td style="text-align: center; vertical-align: middle;">${lastTest}</td>
                <td style="text-align: center;">
                    <button class="btn btn-info" onclick="providersApp.testProviderConnection(${provider.id}, this)">
                        🔍 测试
                    </button>
                    <button class="btn btn-secondary" onclick="providersApp.editProvider(${provider.id})">
                        ✏️ 编辑
                    </button>
                    <button class="btn btn-danger" onclick="providersApp.deleteProvider(${provider.id}, this)">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    // 服务商相关方法
    showProviderModal(providerId = null) {
        this.currentProviderId = providerId;
        const modal = document.getElementById('providerModal');
        const title = document.getElementById('providerModalTitle');
        const form = document.getElementById('providerForm');

        if (modal && title && form) {
            if (providerId) {
                title.textContent = '编辑服务商';
                this.loadProviderData(providerId);
            } else {
                title.textContent = '添加服务商';
                form.reset();
            }

            modal.style.display = 'block';
        }
    }

    async loadProviderData(providerId) {
        try {
            const response = await fetch(`/api/providers/${providerId}`);
            const provider = await response.json();

            document.getElementById('providerName').value = provider.name;
            document.getElementById('providerType').value = provider.type;
            document.getElementById('providerAccessKey').value = provider.access_key;
            document.getElementById('providerSecretKey').value = provider.secret_key;
            document.getElementById('providerEnabled').checked = provider.enabled;
        } catch (error) {
            this.showAlert('providers-alert', '加载服务商数据失败: ' + error.message, 'error');
        }
    }

    closeProviderModal() {
        const modal = document.getElementById('providerModal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.currentProviderId = null;
    }

    async handleProviderSubmit(e) {
        e.preventDefault();

        // 获取提交按钮并显示加载动画
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            this.showLoadingSpinner(submitButton, '保存中...');
        }

        const formData = {
            name: document.getElementById('providerName').value,
            type: parseInt(document.getElementById('providerType').value),
            access_key: document.getElementById('providerAccessKey').value,
            secret_key: document.getElementById('providerSecretKey').value,
            enabled: document.getElementById('providerEnabled').checked
        };

        try {
            const url = this.currentProviderId ? `/api/providers/${this.currentProviderId}` : '/api/providers/';
            const method = this.currentProviderId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.showAlert('providers-alert', '保存成功', 'success');
                this.closeProviderModal();
                this.loadProviders();
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '保存失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('providers-alert', '保存失败: ' + error.message, 'error');
        } finally {
            if (submitButton) {
                this.hideLoadingSpinner(submitButton);
            }
        }
    }

    async updateProviderStatus(providerId, enabled, switchElement = null) {
        try {
            const response = await fetch(`/api/providers/${providerId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled: enabled })
            });

            if (response.ok) {
                this.showAlert('providers-alert', '状态更新成功', 'success');
                this.loadProviders();
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '状态更新失败: ' + error.detail, 'error');
                // 恢复开关状态
                if (switchElement) {
                    switchElement.checked = !enabled;
                }
            }
        } catch (error) {
            this.showAlert('providers-alert', '状态更新失败: ' + error.message, 'error');
            // 恢复开关状态
            if (switchElement) {
                switchElement.checked = !enabled;
            }
        }
    }

    async testProviderConnection(providerId, buttonElement = null) {
        try {
            const response = await this.apiCall(`/api/providers/${providerId}/test`, {
                method: 'POST'
            }, buttonElement, '测试中...');

            if (response.ok) {
                const result = await response.json();
                this.showAlert('providers-alert', result.message, 'success');
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '连接测试失败: ' + error.detail, 'error');
            }

            this.loadProviders();
        } catch (error) {
            this.showAlert('providers-alert', '连接测试失败: ' + error.message, 'error');
        }
    }

    editProvider(providerId) {
        this.showProviderModal(providerId);
    }

    async deleteProvider(providerId, buttonElement = null) {
        if (!confirm('确定要删除这个服务商吗？')) return;

        try {
            const response = await this.apiCall(`/api/providers/${providerId}`, {
                method: 'DELETE'
            }, buttonElement, '删除中...');

            if (response.ok) {
                this.showAlert('providers-alert', '删除成功', 'success');
                this.loadProviders();
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '删除失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('providers-alert', '删除失败: ' + error.message, 'error');
        }
    }


    // 工具方法
    showAlert(containerId, message, type) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Alert container '${containerId}' not found`);
            return;
        }
        container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;

        setTimeout(() => {
            if (container) {
                container.innerHTML = '';
            }
        }, 3000);
    }

    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    showLoadingSpinner(button, text = '处理中...') {
        if (!button) return;
        
        button.dataset.originalText = button.textContent;
        button.dataset.originalDisabled = button.disabled;
        
        button.disabled = true;
        button.innerHTML = `
            <span style="display: inline-block; width: 16px; height: 16px; margin-right: 8px;">
                <svg style="animation: spin 1s linear infinite; width: 16px; height: 16px;" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" opacity="0.25"/>
                    <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"/>
                </svg>
            </span>
            ${text}
        `;
    }

    hideLoadingSpinner(button) {
        if (!button) return;
        
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            button.disabled = button.dataset.originalDisabled === 'true';
            delete button.dataset.originalText;
            delete button.dataset.originalDisabled;
        }
    }

    async apiCall(url, options = {}, buttonElement = null, loadingText = '处理中...') {
        if (buttonElement) {
            this.showLoadingSpinner(buttonElement, loadingText);
        }

        try {
            const response = await fetch(url, options);
            return response;
        } finally {
            if (buttonElement) {
                this.hideLoadingSpinner(buttonElement);
            }
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

// 导出 ProvidersManager 类
window.ProvidersManager = ProvidersManager;

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;
    
    // 初始化服务商管理器
    window.providersApp = new ProvidersManager();
    
    // 创建侧边栏
    const sidebar = new Sidebar();
    
    // 延迟设置服务商管理为当前活跃页面
    setTimeout(() => {
        // 检查当前URL路径
        const currentPath = window.location.pathname;
        const providersNavItem = document.querySelector('[href="/providers"]');
        
        if (providersNavItem && (currentPath === '/' || currentPath === '/providers')) {
            // 清除其他活跃状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            // 设置当前页面为活跃
            providersNavItem.classList.add('active');
        }
    }, 100);
});
