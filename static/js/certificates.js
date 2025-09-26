// 证书管理页面JavaScript

class CertificatesManager {
    constructor() {
        this.currentCertificateId = null;
        this.init();
    }

    init() {
        this.loadCertificates();
        this.loadDomainSelect();
    }

    // 证书管理相关方法
    async loadCertificates() {
        try {
            const response = await fetch('/api/certificates/');
            const certificates = await response.json();
            this.renderCertificates(certificates);
        } catch (error) {
            this.showAlert('certificates-alert', '加载证书列表失败: ' + error.message, 'error');
        }
    }

    async loadDomainSelect() {
        try {
            const response = await fetch('/api/domains/');
            const domains = await response.json();
            
            const select = document.getElementById('certDomainSelect');
            select.innerHTML = '<option value="">🔍 选择域名查看证书</option>';
            
            domains.forEach(domain => {
                const option = document.createElement('option');
                option.value = domain.id;
                option.textContent = `${domain.name} (${domain.provider.name})`;
                select.appendChild(option);
            });
        } catch (error) {
            this.showAlert('certificates-alert', '加载域名列表失败: ' + error.message, 'error');
        }
    }

    async loadCertificatesByDomain() {
        const domainId = document.getElementById('certDomainSelect').value;
        if (!domainId) {
            this.loadCertificates();
            return;
        }

        try {
            const response = await fetch(`/api/certificates/domain/${domainId}`);
            const certificates = await response.json();
            this.renderCertificates(certificates);
        } catch (error) {
            this.showAlert('certificates-alert', '加载证书列表失败: ' + error.message, 'error');
        }
    }

    async loadExpiringCertificates() {
        try {
            const response = await fetch('/api/certificates/expiring/soon?days=30');
            const certificates = await response.json();
            this.renderCertificates(certificates);
        } catch (error) {
            this.showAlert('certificates-alert', '加载即将过期证书失败: ' + error.message, 'error');
        }
    }

    canRenewCertificate(cert) {
        // 检查证书是否在30天内过期
        if (!cert.not_after) {
            return false; // 没有过期时间信息，不允许续期
        }
        
        const now = new Date();
        const expiryDate = new Date(cert.not_after);
        const daysUntilExpiry = Math.ceil((expiryDate - now) / (1000 * 60 * 60 * 24));
        
        // 只有在30天内过期且证书状态为有效时才允许续期
        return daysUntilExpiry <= 30 && daysUntilExpiry > 0 && cert.status === 1;
    }

    renderCertificates(certificates) {
        const tbody = document.getElementById('certificates-table');
        tbody.innerHTML = '';

        if (certificates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">没有找到证书记录</td></tr>';
            return;
        }

        certificates.forEach(cert => {
            const row = document.createElement('tr');
            const statusClass = this.getCertificateStatusClass(cert.status);
            const statusText = this.getCertificateStatusText(cert.status);
            const typeText = this.getCertificateTypeText(cert.type);
            const notBefore = cert.not_before ? new Date(cert.not_before).toLocaleDateString() : '-';
            const notAfter = cert.not_after ? new Date(cert.not_after).toLocaleDateString() : '-';
            
            // 检查证书是否在30天内过期
            const canRenew = this.canRenewCertificate(cert);
            const renewButtonClass = canRenew ? 'btn btn-secondary' : 'btn btn-secondary disabled';
            const renewButtonTitle = canRenew ? '续期证书' : '证书有效期超过30天，暂不可续期';
            const renewButtonDisabled = canRenew ? '' : 'disabled';

            row.innerHTML = `
                <td style="text-align: center;">${cert.name}</td>
                <td style="text-align: center;">${cert.domain.name}</td>
                <td style="text-align: center;">${typeText}</td>
                <td style="text-align: center;">${cert.issuer || '-'}</td>
                <td style="text-align: center;">${notBefore}</td>
                <td style="text-align: center;">${notAfter}</td>
                <td style="text-align: center;"><span class="status ${statusClass}">${statusText}</span></td>
                <td style="text-align: center;">
                    <label class="switch">
                        <input type="checkbox" ${cert.auto_renew ? 'checked' : ''} 
                               onchange="certificatesApp.toggleCertificateAutoRenew(${cert.id}, this.checked)">
                        <span class="slider"></span>
                    </label>
                </td>
                <td style="text-align: center;">
                    <button class="btn btn-primary" onclick="certificatesApp.checkCertificateStatus(${cert.id})">
                        🔍 检查
                    </button>
                    <button class="${renewButtonClass}" onclick="certificatesApp.renewCertificate(${cert.id}, this)" 
                            title="${renewButtonTitle}" ${renewButtonDisabled}>
                        🔄 续期
                    </button>
                    <button class="btn btn-success" onclick="certificatesApp.downloadCertificate(${cert.id})">
                        📥 下载
                    </button>
                    <button class="btn btn-danger" onclick="certificatesApp.deleteCertificate(${cert.id}, this)">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    getCertificateStatusClass(status) {
        const statusMap = {
            1: 'enabled',    // VALID
            2: 'disabled',   // EXPIRED
            3: 'warning',    // EXPIRING_SOON
            4: 'disabled',   // INVALID
            5: 'pending'     // PENDING
        };
        return statusMap[status] || 'pending';
    }

    getCertificateStatusText(status) {
        const statusMap = {
            1: '有效',
            2: '已过期',
            3: '即将过期',
            4: '无效',
            5: '待处理'
        };
        return statusMap[status] || '未知';
    }

    getCertificateTypeText(type) {
        const typeMap = {
            1: 'Let\'s Encrypt',
            2: '自定义',
            3: '自签名'
        };
        return typeMap[type] || '未知';
    }

    async toggleCertificateAutoRenew(certificateId, autoRenew) {
        try {
            const response = await fetch(`/api/certificates/${certificateId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ auto_renew: autoRenew })
            });

            if (response.ok) {
                this.showAlert('certificates-alert', '自动续期设置更新成功', 'success');
            } else {
                const error = await response.json();
                this.showAlert('certificates-alert', '更新失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '更新失败: ' + error.message, 'error');
        }
    }

    async checkCertificateStatus(certificateId) {
        try {
            const response = await fetch(`/api/certificates/check-status/${certificateId}`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showAlert('certificates-alert', '证书状态检查完成', 'success');
                this.loadCertificates();
            } else {
                this.showAlert('certificates-alert', '状态检查失败: ' + result.message, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '状态检查失败: ' + error.message, 'error');
        }
    }

    async renewCertificate(certificateId, buttonElement = null) {
        // 检查按钮是否被禁用
        if (buttonElement && buttonElement.disabled) {
            this.showAlert('certificates-alert', '证书有效期超过30天，暂不可续期', 'warning');
            return;
        }

        if (!confirm('确定要续期这个证书吗？')) return;

        try {
            const response = await this.apiCall(`/api/certificates/renew/${certificateId}`, {
                method: 'POST'
            }, buttonElement, '续期中...');

            if (response.ok) {
                const result = await response.json();
                this.showAlert('certificates-alert', result.message, 'success');
                this.loadCertificates();
            } else {
                const error = await response.json();
                this.showAlert('certificates-alert', '续期失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '续期失败: ' + error.message, 'error');
        }
    }

    showCertificateModal(certificateId = null) {
        this.currentCertificateId = certificateId;
        this.showRequestCertificateModal();
    }

    async showRequestCertificateModal() {
        // 获取域名列表
        try {
            const response = await fetch('/api/domains/');
            const domains = await response.json();
            
            if (domains.length === 0) {
                this.showAlert('certificates-alert', '请先添加域名', 'warning');
                return;
            }
            
            // 创建申请证书模态框
            const modalContent = `
                <div class="modal" id="requestCertificateModal" style="display: block;">
                    <div class="modal-content" style="max-width: 600px;">
                        <div class="modal-header">
                            <h3>申请SSL证书</h3>
                            <span class="close" onclick="certificatesApp.closeRequestCertificateModal()">&times;</span>
                        </div>
                        <div class="modal-body">
                            <form id="requestCertificateForm">
                                <div class="form-group">
                                    <label for="certificateDomain">选择域名</label>
                                    <select id="certificateDomain" required>
                                        <option value="">请选择域名</option>
                                        ${domains.map(domain => `<option value="${domain.id}">${domain.name}</option>`).join('')}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="certificateSubdomain">子域名（可选）</label>
                                    <input type="text" id="certificateSubdomain" placeholder="例如: www, api, home">
                                    <small class="form-text">留空则申请主域名证书</small>
                                </div>
                                <div class="form-group">
                                    <label for="certificateName">证书名称</label>
                                    <input type="text" id="certificateName" required placeholder="证书显示名称">
                                </div>
                                <div class="form-group">
                                    <label class="switch-container">
                                        <span>自动续期</span>
                                        <label class="switch">
                                            <input type="checkbox" id="certificateAutoRenew" checked>
                                            <span class="slider"></span>
                                        </label>
                                    </label>
                                </div>
                                <div style="text-align: right; margin-top: 2rem;">
                                    <button type="button" class="btn btn-secondary" onclick="certificatesApp.closeRequestCertificateModal()">取消</button>
                                    <button type="submit" class="btn btn-primary">申请证书</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            // 移除已存在的模态框
            const existingModal = document.getElementById('requestCertificateModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // 添加新模态框
            document.body.insertAdjacentHTML('beforeend', modalContent);
            
            // 绑定表单提交事件
            document.getElementById('requestCertificateForm').addEventListener('submit', (e) => {
                this.handleRequestCertificate(e);
            });
            
            // 绑定域名选择事件
            document.getElementById('certificateDomain').addEventListener('change', (e) => {
                this.updateCertificateName(e.target.value);
            });
            
            // 绑定子域名输入事件
            document.getElementById('certificateSubdomain').addEventListener('input', (e) => {
                const domainId = document.getElementById('certificateDomain').value;
                if (domainId) {
                    this.updateCertificateName(domainId);
                }
            });
            
        } catch (error) {
            this.showAlert('certificates-alert', '加载域名列表失败: ' + error.message, 'error');
        }
    }

    updateCertificateName(domainId) {
        const domainSelect = document.getElementById('certificateDomain');
        const subdomainInput = document.getElementById('certificateSubdomain');
        const nameInput = document.getElementById('certificateName');
        
        if (domainId) {
            const domainName = domainSelect.options[domainSelect.selectedIndex].text;
            const subdomain = subdomainInput.value.trim();
            
            // 自动生成证书名称
            if (subdomain) {
                nameInput.value = `${subdomain}.${domainName}`;
            } else {
                nameInput.value = `${domainName}`;
            }
        } else {
            // 清空证书名称
            nameInput.value = '';
        }
    }

    async handleRequestCertificate(e) {
        e.preventDefault();
        
        // 获取提交按钮并显示加载动画
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            this.showLoadingSpinner(submitButton, '申请中...');
        }

        // 构建完整域名
        const domainSelect = document.getElementById('certificateDomain');
        const domainName = domainSelect.options[domainSelect.selectedIndex].text;
        const subdomainPrefix = document.getElementById('certificateSubdomain').value.trim();
        
        let fullDomain;
        if (subdomainPrefix) {
            fullDomain = `${subdomainPrefix}.${domainName}`;
        } else {
            fullDomain = domainName;
        }

        const formData = {
            domain_id: parseInt(document.getElementById('certificateDomain').value),
            full_domain: fullDomain,
            subdomain: subdomainPrefix || null,
            name: document.getElementById('certificateName').value,
            auto_renew: document.getElementById('certificateAutoRenew').checked
        };

        try {
            const response = await fetch(`/api/certificates/request/${formData.domain_id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    subdomain: formData.subdomain,
                    full_domain: formData.full_domain,
                    name: formData.name,
                    auto_renew: formData.auto_renew
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.showAlert('certificates-alert', result.message, 'success');
                this.closeRequestCertificateModal();
                this.loadCertificates(); // 重新加载证书列表
            } else {
                const error = await response.json();
                this.showAlert('certificates-alert', '申请证书失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '申请证书失败: ' + error.message, 'error');
        } finally {
            // 隐藏加载动画
            if (submitButton) {
                this.hideLoadingSpinner(submitButton);
            }
        }
    }

    closeRequestCertificateModal() {
        const modal = document.getElementById('requestCertificateModal');
        if (modal) {
            modal.remove();
        }
    }

    async downloadCertificate(certificateId) {
        try {
            const response = await fetch(`/api/certificates/${certificateId}/download`);
            
            if (!response.ok) {
                throw new Error('下载失败');
            }
            
            // 获取证书信息用于文件名
            const certResponse = await fetch(`/api/certificates/${certificateId}`);
            const certData = await certResponse.json();
            
            // 创建下载链接
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${certData.name || 'certificate'}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showAlert('certificates-alert', '证书下载成功', 'success');
        } catch (error) {
            this.showAlert('certificates-alert', '下载失败: ' + error.message, 'error');
        }
    }

    async deleteCertificate(certificateId, buttonElement = null) {
        if (!confirm('确定要删除这个证书吗？')) return;

        try {
            const response = await this.apiCall(`/api/certificates/${certificateId}`, {
                method: 'DELETE'
            }, buttonElement, '删除中...');

            if (response.ok) {
                this.showAlert('certificates-alert', '证书删除成功', 'success');
                this.loadCertificates();
            } else {
                const error = await response.json();
                this.showAlert('certificates-alert', '删除失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '删除失败: ' + error.message, 'error');
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

// 初始化证书管理应用
let certificatesApp;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;
    
    // 初始化证书管理器
    certificatesApp = new CertificatesManager();
    window.certificatesApp = certificatesApp; // 确保全局可访问
    
    // 创建侧边栏
    const sidebar = new Sidebar();
    
    // 延迟设置证书管理为当前活跃页面
    setTimeout(() => {
        const certificatesNavItem = document.querySelector('[href="/certificates"]');
        if (certificatesNavItem) {
            // 清除其他活跃状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            // 设置当前页面为活跃
            certificatesNavItem.classList.add('active');
        }
    }, 100);
});
