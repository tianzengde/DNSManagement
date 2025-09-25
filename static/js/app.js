// 主应用文件
class DNSManager {
    constructor() {
        this.currentSection = 'providers';
        this.currentProviderId = null;
        this.currentDomainId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadProviders();
        this.loadProviderSelect();
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

        // 表单提交
        document.getElementById('providerForm')?.addEventListener('submit', (e) => {
            this.handleProviderSubmit(e);
        });

        document.getElementById('domainForm')?.addEventListener('submit', (e) => {
            this.handleDomainSubmit(e);
        });
    }

    showSection(sectionName) {
        // 隐藏所有区域
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });

        // 移除所有导航项的active类
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // 显示选中的区域
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.add('active');
        }

        // 为当前导航项添加active类
        const navItem = document.querySelector(`[data-section="${sectionName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        }

        this.currentSection = sectionName;

        // 根据区域加载相应数据
        if (sectionName === 'providers') {
            this.loadProviders();
        } else if (sectionName === 'domains') {
            this.loadProviderSelect();
        } else if (sectionName === 'certificates') {
            this.loadCertificates();
            this.loadDomainSelect();
        }
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
        tbody.innerHTML = '';

        providers.forEach(provider => {
            const row = document.createElement('tr');
            const statusClass = provider.status === 'connected' ? 'enabled' : 'disabled';
            const statusText = provider.status === 'connected' ? '已连接' : 
                             provider.status === 'failed' ? '连接失败' : 
                             provider.status === 'error' ? '错误' : '未知';
            const lastTest = provider.last_test_at ? 
                new Date(provider.last_test_at).toLocaleString() : '未测试';

            row.innerHTML = `
                <td>${provider.id}</td>
                <td>${provider.name}</td>
                <td>${provider.type === 1 ? '华为云' : '阿里云'}</td>
                <td>
                    <label class="switch">
                        <input type="checkbox" ${provider.enabled ? 'checked' : ''} 
                               onchange="app.toggleProvider(${provider.id}, this.checked)">
                        <span class="slider"></span>
                    </label>
                </td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>${lastTest}</td>
                <td>
                    <button class="btn btn-primary" onclick="app.testProvider(${provider.id})">
                        🔍 测试
                    </button>
                    <button class="btn btn-success" onclick="app.syncProvider(${provider.id})">
                        🔄 同步
                    </button>
                    <button class="btn btn-secondary" onclick="app.editProvider(${provider.id})">
                        ✏️ 编辑
                    </button>
                    <button class="btn btn-danger" onclick="app.deleteProvider(${provider.id})">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadProviderSelect() {
        try {
            const response = await fetch('/api/providers/');
            const providers = await response.json();
            
            const select = document.getElementById('providerSelect');
            select.innerHTML = '<option value="">🔍 选择服务商查看域名</option>';
            
            providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.id;
                option.textContent = `${provider.name} (${provider.type === 1 ? '华为云' : '阿里云'})`;
                select.appendChild(option);
            });
        } catch (error) {
            this.showAlert('domains-alert', '加载服务商列表失败: ' + error.message, 'error');
        }
    }

    async loadProviderDomains() {
        const providerId = document.getElementById('providerSelect').value;
        if (!providerId) {
            document.getElementById('domains-table').innerHTML = '';
            return;
        }

        try {
            // 从数据库获取域名记录，而不是直接请求服务商
            const response = await fetch(`/api/domains/?provider_id=${providerId}`);
            const domains = await response.json();
            this.renderDomainsFromDB(domains, providerId);
        } catch (error) {
            this.showAlert('domains-alert', '加载域名列表失败: ' + error.message, 'error');
        }
    }

    renderDomains(domains, providerId) {
        const tbody = document.getElementById('domains-table');
        tbody.innerHTML = '';

        if (domains.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">该服务商下没有域名记录</td></tr>';
            return;
        }

        domains.forEach(record => {
            const row = document.createElement('tr');
            const statusClass = record.status === 'ACTIVE' ? 'enabled' : 'disabled';
            const statusText = record.status === 'ACTIVE' ? '活跃' : 
                             record.status === 'PENDING' ? '等待中' : 
                             record.status === 'UNKNOWN' ? '未知' : record.status || '未知';

            row.innerHTML = `
                <td>${record.name}</td>
                <td>${record.domain}</td>
                <td>${record.provider_name}</td>
                <td>${record.type || '-'}</td>
                <td>${record.records && record.records.length > 0 ? record.records.join(', ') : '-'}</td>
                <td>${record.ttl || '-'}</td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn btn-primary" onclick="app.editRecord(${providerId}, '${record.name}', '${record.type}')">
                        ✏️ 编辑
                    </button>
                    <button class="btn btn-danger" onclick="app.deleteRecord(${providerId}, '${record.name}', '${record.type}')">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderDomainsFromDB(domains, providerId) {
        const tbody = document.getElementById('domains-table');
        tbody.innerHTML = '';

        if (domains.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">该服务商下没有域名记录</td></tr>';
            return;
        }

        // 收集所有DNS记录
        const domainRecords = {};
        domains.forEach(domain => {
            if (domain.records && domain.records.length > 0) {
                domain.records.forEach(record => {
                    const key = `${record.name}_${record.type}`;
                    if (!domainRecords[key]) {
                        domainRecords[key] = {
                            name: record.name,
                            type: this.getRecordTypeText(record.type),
                            value: record.value,
                            ttl: record.ttl,
                            status: record.enabled ? 'ACTIVE' : 'DISABLED',
                            domain: domain.name,
                            provider_name: domain.provider.name
                        };
                    }
                });
            }
        });

        // 渲染记录
        const records = Object.values(domainRecords);
        if (records.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">该服务商下没有DNS记录</td></tr>';
            return;
        }

        records.forEach(record => {
            const row = document.createElement('tr');
            const statusClass = record.status === 'ACTIVE' ? 'enabled' : 'disabled';
            const statusText = record.status === 'ACTIVE' ? '活跃' : '禁用';

            row.innerHTML = `
                <td>${record.name}</td>
                <td>${record.domain}</td>
                <td>${record.provider_name}</td>
                <td>${record.type}</td>
                <td>${record.value}</td>
                <td>${record.ttl}</td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn btn-primary" onclick="app.editRecord(${providerId}, '${record.name}', '${record.type}')">
                        ✏️ 编辑
                    </button>
                    <button class="btn btn-danger" onclick="app.deleteRecord(${providerId}, '${record.name}', '${record.type}')">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    getRecordTypeText(type) {
        const typeMap = {
            1: 'A',
            2: 'AAAA',
            3: 'CNAME',
            4: 'MX',
            5: 'TXT',
            6: 'NS'
        };
        return typeMap[type] || '未知';
    }

    // 服务商相关方法
    showProviderModal(providerId = null) {
        this.currentProviderId = providerId;
        const modal = document.getElementById('providerModal');
        const title = document.getElementById('providerModalTitle');
        const form = document.getElementById('providerForm');

        if (providerId) {
            title.textContent = '编辑服务商';
            this.loadProviderData(providerId);
        } else {
            title.textContent = '添加服务商';
            form.reset();
        }

        modal.style.display = 'block';
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
        document.getElementById('providerModal').style.display = 'none';
        this.currentProviderId = null;
    }

    async handleProviderSubmit(e) {
        e.preventDefault();

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
                    'Content-Type': 'application/json',
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
        }
    }

    async toggleProvider(providerId, enabled) {
        try {
            const response = await fetch(`/api/providers/${providerId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ enabled: enabled })
            });

            if (response.ok) {
                this.showAlert('providers-alert', '状态更新成功', 'success');
                this.loadProviders();
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '状态更新失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('providers-alert', '状态更新失败: ' + error.message, 'error');
        }
    }

    async testProvider(providerId) {
        try {
            const response = await fetch(`/api/providers/${providerId}/test`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                this.showAlert('providers-alert', '连接测试成功', 'success');
            } else {
                this.showAlert('providers-alert', '连接测试失败: ' + result.message, 'error');
            }

            this.loadProviders();
        } catch (error) {
            this.showAlert('providers-alert', '连接测试失败: ' + error.message, 'error');
        }
    }

    editProvider(providerId) {
        this.showProviderModal(providerId);
    }

    async deleteProvider(providerId) {
        if (!confirm('确定要删除这个服务商吗？')) return;

        try {
            const response = await fetch(`/api/providers/${providerId}`, {
                method: 'DELETE'
            });

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

    async syncProvider(providerId) {
        try {
            const response = await fetch(`/api/providers/${providerId}/sync`, {
                method: 'POST'
            });

            if (response.ok) {
                this.showAlert('providers-alert', '同步任务已启动，请稍后查看结果', 'success');
            } else {
                const error = await response.json();
                this.showAlert('providers-alert', '启动同步失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('providers-alert', '启动同步失败: ' + error.message, 'error');
        }
    }

    async syncAllProviders() {
        if (!confirm('确定要同步所有服务商的域名吗？这可能需要一些时间。')) return;

        try {
            // 获取所有启用的服务商并逐个同步
            const response = await fetch('/api/providers/');
            const providers = await response.json();
            
            const enabledProviders = providers.filter(p => p.enabled);
            let syncCount = 0;
            
            for (const provider of enabledProviders) {
                try {
                    await this.syncProvider(provider.id);
                    syncCount++;
                } catch (error) {
                    console.error(`同步服务商 ${provider.name} 失败:`, error);
                }
            }
            
            this.showAlert('providers-alert', `已启动 ${syncCount} 个服务商的同步任务`, 'success');
        } catch (error) {
            this.showAlert('providers-alert', '同步失败: ' + error.message, 'error');
        }
    }

    async showSyncStatus() {
        try {
            const response = await fetch('/api/providers/sync/status');
            const status = await response.json();
            
            let statusText = '同步任务状态:\n';
            status.jobs.forEach(job => {
                const nextRun = job.next_run_time ? new Date(job.next_run_time).toLocaleString() : '无';
                statusText += `• ${job.name}: 下次运行 ${nextRun}\n`;
            });
            
            alert(statusText);
        } catch (error) {
            this.showAlert('providers-alert', '获取同步状态失败: ' + error.message, 'error');
        }
    }

    // 域名相关方法
    showDomainModal(domainId = null) {
        this.currentDomainId = domainId;
        const modal = document.getElementById('domainModal');
        const title = document.getElementById('domainModalTitle');
        const form = document.getElementById('domainForm');

        if (domainId) {
            title.textContent = '编辑域名';
            this.loadDomainData(domainId);
        } else {
            title.textContent = '添加域名';
            form.reset();
        }

        modal.style.display = 'block';
    }

    async loadDomainData(domainId) {
        try {
            const response = await fetch(`/api/domains/${domainId}`);
            const domain = await response.json();

            document.getElementById('domainName').value = domain.name;
            document.getElementById('domainProvider').value = domain.provider_id;
            document.getElementById('domainEnabled').checked = domain.enabled;
            document.getElementById('domainAutoUpdate').checked = domain.auto_update;
        } catch (error) {
            this.showAlert('domains-alert', '加载域名数据失败: ' + error.message, 'error');
        }
    }

    closeDomainModal() {
        document.getElementById('domainModal').style.display = 'none';
        this.currentDomainId = null;
    }

    async handleDomainSubmit(e) {
        e.preventDefault();

        const formData = {
            name: document.getElementById('domainName').value,
            provider_id: parseInt(document.getElementById('domainProvider').value),
            enabled: document.getElementById('domainEnabled').checked,
            auto_update: document.getElementById('domainAutoUpdate').checked
        };

        try {
            const url = this.currentDomainId ? `/api/domains/${this.currentDomainId}` : '/api/domains/';
            const method = this.currentDomainId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.showAlert('domains-alert', '保存成功', 'success');
                this.closeDomainModal();
                this.loadProviderDomains();
            } else {
                const error = await response.json();
                this.showAlert('domains-alert', '保存失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('domains-alert', '保存失败: ' + error.message, 'error');
        }
    }

    editRecord(providerId, recordName, recordType) {
        this.showAlert('domains-alert', '编辑记录功能待实现', 'error');
    }

    async deleteRecord(providerId, recordName, recordType) {
        if (!confirm(`确定要删除记录 ${recordName} (${recordType}) 吗？`)) return;

        try {
            const response = await fetch(`/api/providers/${providerId}/records/${encodeURIComponent(recordName)}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('domains-alert', '记录删除成功', 'success');
                this.loadProviderDomains();
            } else {
                const error = await response.json();
                this.showAlert('domains-alert', '删除失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('domains-alert', '删除失败: ' + error.message, 'error');
        }
    }

    // 工具方法
    showAlert(containerId, message, type) {
        const container = document.getElementById(containerId);
        container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;

        setTimeout(() => {
            container.innerHTML = '';
        }, 3000);
    }

    closeModal(modal) {
        modal.style.display = 'none';
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

            row.innerHTML = `
                <td>${cert.name}</td>
                <td>${cert.domain.name}</td>
                <td>${typeText}</td>
                <td>${cert.issuer || '-'}</td>
                <td>${notBefore}</td>
                <td>${notAfter}</td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>
                    <label class="switch">
                        <input type="checkbox" ${cert.auto_renew ? 'checked' : ''} 
                               onchange="app.toggleCertificateAutoRenew(${cert.id}, this.checked)">
                        <span class="slider"></span>
                    </label>
                </td>
                <td>
                    <button class="btn btn-primary" onclick="app.checkCertificateStatus(${cert.id})">
                        🔍 检查
                    </button>
                    <button class="btn btn-secondary" onclick="app.renewCertificate(${cert.id})">
                        🔄 续期
                    </button>
                    <button class="btn btn-warning" onclick="app.editCertificate(${cert.id})">
                        ✏️ 编辑
                    </button>
                    <button class="btn btn-danger" onclick="app.deleteCertificate(${cert.id})">
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

    async renewCertificate(certificateId) {
        if (!confirm('确定要续期这个证书吗？')) return;

        try {
            const response = await fetch(`/api/certificates/${certificateId}/renew`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ certificate_id: certificateId, force: false })
            });
            const result = await response.json();

            if (result.success) {
                this.showAlert('certificates-alert', '证书续期成功', 'success');
                this.loadCertificates();
            } else {
                this.showAlert('certificates-alert', '续期失败: ' + result.message, 'error');
            }
        } catch (error) {
            this.showAlert('certificates-alert', '续期失败: ' + error.message, 'error');
        }
    }

    showCertificateModal(certificateId = null) {
        this.currentCertificateId = certificateId;
        // 这里应该创建证书模态框，暂时显示提示
        this.showAlert('certificates-alert', '证书管理功能开发中...', 'warning');
    }

    editCertificate(certificateId) {
        this.showCertificateModal(certificateId);
    }

    async deleteCertificate(certificateId) {
        if (!confirm('确定要删除这个证书吗？')) return;

        try {
            const response = await fetch(`/api/certificates/${certificateId}`, {
                method: 'DELETE'
            });

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
}

// 全局变量
let app;

// 页面加载完成后初始化（这个会被HTML中的初始化覆盖）
document.addEventListener('DOMContentLoaded', function() {
    if (!window.app) {
        app = new DNSManager();
        window.app = app;
    }
});
