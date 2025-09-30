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
                2: '阿里云',
                3: '腾讯云',
                4: 'Cloudflare'
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
                    <button class="btn btn-success" onclick="providersApp.syncProviderDomains(${provider.id}, this)">
                        🔄 同步
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
                // 初始化字段状态
                this.initializeFormFields();
            }

            modal.style.display = 'block';
        }
    }
    
    initializeFormFields() {
        // 确保默认状态下传统字段有required属性
        document.getElementById('providerAccessKey').setAttribute('required', 'required');
        document.getElementById('providerSecretKey').setAttribute('required', 'required');
        document.getElementById('providerToken').removeAttribute('required');
        // 确保默认显示传统字段
        document.getElementById('traditionalKeys').style.display = 'block';
        document.getElementById('cloudflareToken').style.display = 'none';
    }

    async loadProviderData(providerId) {
        try {
            const response = await fetch(`/api/providers/${providerId}`);
            const provider = await response.json();

            document.getElementById('providerName').value = provider.name;
            document.getElementById('providerType').value = provider.type;
            document.getElementById('providerEnabled').checked = provider.enabled;
            
            // 根据提供商类型填充不同的字段
            if (provider.type === 4) { // Cloudflare
                document.getElementById('providerToken').value = provider.access_key;
                document.getElementById('providerEmail').value = provider.secret_key || '';
            } else { // 华为云、阿里云、腾讯云
                document.getElementById('providerAccessKey').value = provider.access_key;
                document.getElementById('providerSecretKey').value = provider.secret_key;
                document.getElementById('providerRegion').value = provider.region || '';
            }
            
            // 触发帮助信息显示和字段切换
            this.showProviderHelp(provider.type.toString());
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

        const providerType = parseInt(document.getElementById('providerType').value);
        let formData;
        
        if (providerType === 4) { // Cloudflare
            const token = document.getElementById('providerToken').value;
            if (!token) {
                this.showAlert('providers-alert', '请输入Cloudflare API Token', 'error');
                return;
            }
            formData = {
                name: document.getElementById('providerName').value,
                type: providerType,
                access_key: token,
                secret_key: document.getElementById('providerEmail').value || '',
                enabled: document.getElementById('providerEnabled').checked
            };
        } else { // 华为云、阿里云、腾讯云
            formData = {
                name: document.getElementById('providerName').value,
                type: providerType,
                access_key: document.getElementById('providerAccessKey').value,
                secret_key: document.getElementById('providerSecretKey').value,
                region: document.getElementById('providerRegion').value || '',
                enabled: document.getElementById('providerEnabled').checked
            };
        }

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

    async syncProviderDomains(providerId, buttonElement = null) {
        try {
            const response = await this.apiCall(`/api/providers/${providerId}/sync`, {
                method: 'POST'
            }, buttonElement, '同步中...');

            if (response.ok) {
                const result = await response.json();
                this.showAlert('providers-alert', result.message, 'success');
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '同步失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('providers-alert', '同步失败: ' + error.message, 'error');
        }
    }

    async syncAllProviders(buttonElement = null) {
        if (!confirm('确定要同步所有服务商的域名吗？这可能需要一些时间。')) return;

        try {
            // 显示加载动画
            if (buttonElement) {
                this.showLoadingSpinner(buttonElement, '同步中...');
            }

            const response = await fetch('/api/providers/');
            const providers = await response.json();
            
            const enabledProviders = providers.filter(p => p.enabled);
            let syncCount = 0;
            
            for (const provider of enabledProviders) {
                try {
                    await this.syncProviderDomains(provider.id);
                    syncCount++;
                } catch (error) {
                    console.error(`同步服务商 ${provider.name} 失败:`, error);
                }
            }
            
            this.showAlert('providers-alert', `批量同步完成，成功同步 ${syncCount} 个服务商`, 'success');
        } catch (error) {
            this.showAlert('providers-alert', '批量同步失败: ' + error.message, 'error');
        } finally {
            if (buttonElement) {
                this.hideLoadingSpinner(buttonElement);
            }
        }
    }

    showSyncStatus() {
        // 显示同步状态概览
        alert('同步状态功能待实现');
    }

    // 显示服务商帮助信息
    showProviderHelp(providerType) {
        const helpDiv = document.getElementById('providerHelp');
        const helpTitle = document.getElementById('helpTitle');
        const helpContent = document.getElementById('helpContent');
        const traditionalKeys = document.getElementById('traditionalKeys');
        const cloudflareToken = document.getElementById('cloudflareToken');
        
        if (!providerType) {
            helpDiv.style.display = 'none';
            traditionalKeys.style.display = 'block';
            cloudflareToken.style.display = 'none';
            return;
        }
        
        // 切换输入字段显示
        if (providerType === '4') { // Cloudflare
            traditionalKeys.style.display = 'none';
            cloudflareToken.style.display = 'block';
            // 移除传统字段的required属性，避免表单验证错误
            document.getElementById('providerAccessKey').removeAttribute('required');
            document.getElementById('providerSecretKey').removeAttribute('required');
            // 为Cloudflare Token添加required属性
            document.getElementById('providerToken').setAttribute('required', 'required');
        } else { // 华为云、阿里云、腾讯云
            traditionalKeys.style.display = 'block';
            cloudflareToken.style.display = 'none';
            // 恢复传统字段的required属性
            document.getElementById('providerAccessKey').setAttribute('required', 'required');
            document.getElementById('providerSecretKey').setAttribute('required', 'required');
            // 移除Cloudflare Token的required属性
            document.getElementById('providerToken').removeAttribute('required');
        }
        
        const helpData = this.getProviderHelpData(providerType);
        helpTitle.textContent = helpData.title;
        helpContent.innerHTML = helpData.content;
        helpDiv.style.display = 'block';
    }

    getProviderHelpData(providerType) {
        const helpData = {
            '1': {
                title: '华为云密钥获取说明',
                content: `
                    <div class="help-steps">
                        <h5>📋 获取步骤：</h5>
                        <ol>
                            <li>登录 <a href="https://console.huaweicloud.com/" target="_blank">华为云控制台</a></li>
                            <li>访问 <a href="https://console.huaweicloud.com/iam/?locale=zh-cn#/mine/accessKey" target="_blank">API凭证管理</a></li>
                            <li>创建访问密钥，获取 Access Key ID 和 Secret Access Key</li>
                            <li>确保账号有 DNS 解析权限</li>
                        </ol>
                        <div class="help-note">
                            <strong>💡 提示：</strong>
                            <ul>
                                <li>访问密钥：Access Key ID</li>
                                <li>秘密密钥：Secret Access Key</li>
                                <li>区域：如 cn-north-4（可选）</li>
                            </ul>
                        </div>
                    </div>
                `
            },
            '2': {
                title: '阿里云密钥获取说明',
                content: `
                    <div class="help-steps">
                        <h5>📋 获取步骤：</h5>
                        <ol>
                            <li>登录 <a href="https://ecs.console.aliyun.com/" target="_blank">阿里云控制台</a></li>
                            <li>访问 <a href="https://ram.console.aliyun.com/profile/access-keys" target="_blank">AccessKey管理</a></li>
                            <li>创建AccessKey，获取 Access Key ID 和 Access Key Secret</li>
                            <li>确保账号有 DNS 解析权限</li>
                        </ol>
                        <div class="help-note">
                            <strong>💡 提示：</strong>
                            <ul>
                                <li>访问密钥：Access Key ID</li>
                                <li>秘密密钥：Access Key Secret</li>
                                <li>区域：DNS服务为全局服务（可选）</li>
                            </ul>
                        </div>
                    </div>
                `
            },
            '3': {
                title: '腾讯云密钥获取说明',
                content: `
                    <div class="help-steps">
                        <h5>📋 获取步骤：</h5>
                        <ol>
                            <li>登录 <a href="https://console.cloud.tencent.com/" target="_blank">腾讯云控制台</a></li>
                            <li>访问 <a href="https://console.dnspod.cn/account/token/apikey" target="_blank">API密钥管理</a></li>
                            <li>创建API密钥，获取 SecretId 和 SecretKey</li>
                            <li>确保账号有 DNS 解析权限</li>
                        </ol>
                        <div class="help-note">
                            <strong>💡 提示：</strong>
                            <ul>
                                <li>访问密钥：SecretId</li>
                                <li>秘密密钥：SecretKey</li>
                                <li>区域：如 ap-beijing（可选）</li>
                            </ul>
                        </div>
                    </div>
                `
            },
            '4': {
                title: 'Cloudflare密钥获取说明',
                content: `
                    <div class="help-steps">
                        <h5>📋 获取步骤：</h5>
                        <ol>
                            <li>登录 <a href="https://dash.cloudflare.com/" target="_blank">Cloudflare控制台</a></li>
                            <li>访问 <a href="https://dash.cloudflare.com/profile/api-tokens" target="_blank">API Tokens</a></li>
                            <li>创建自定义Token，权限设置为：</li>
                            <ul>
                                <li>Zone:Zone:Read</li>
                                <li>Zone:DNS:Edit</li>
                            </ul>
                            <li>将Token作为访问密钥，邮箱作为秘密密钥</li>
                        </ol>
                        <div class="help-note">
                            <strong>💡 提示：</strong>
                            <ul>
                                <li>访问密钥：API Token</li>
                                <li>秘密密钥：邮箱地址（可选）</li>
                                <li>区域：不需要</li>
                            </ul>
                        </div>
                    </div>
                `
            }
        };
        
        return helpData[providerType] || { title: '未知服务商', content: '请选择有效的服务商类型' };
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

// 全局函数，供HTML调用
window.showProviderHelp = function(providerType) {
    if (window.providersApp) {
        window.providersApp.showProviderHelp(providerType);
    }
};

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
