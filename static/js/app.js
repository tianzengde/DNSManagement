// 主应用文件
class DNSManager {
    constructor() {
        this.currentSection = 'providers';
        this.currentProviderId = null;
        this.currentDomainId = null;
        this.init();
    }

    init() {
        this.createModals();
        this.bindEvents();
        this.loadProviders();
        this.loadProviderSelect();
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

        // 表单提交
        document.getElementById('providerForm')?.addEventListener('submit', (e) => {
            this.handleProviderSubmit(e);
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
            this.loadDomains(); // 默认加载全部域名
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
                <td style="text-align: center; vertical-align: middle;">${provider.id}</td>
                <td style="text-align: center; vertical-align: middle;">${provider.name}</td>
                <td style="text-align: center; vertical-align: middle;">${provider.type === 1 ? '华为云' : '阿里云'}</td>
                <td style="text-align: center; vertical-align: middle;">
                    <label class="switch">
                        <input type="checkbox" ${provider.enabled ? 'checked' : ''} 
                               onchange="app.toggleProvider(${provider.id}, this.checked, this)">
                        <span class="slider"></span>
                    </label>
                </td>
                <td style="text-align: center; vertical-align: middle;"><span class="status ${statusClass}" style="display: inline-block; white-space: nowrap;">${statusText}</span></td>
                <td style="text-align: center; vertical-align: middle;">${lastTest}</td>
                <td style="text-align: center; vertical-align: middle;">
                    <div style="display: flex; gap: 6px; justify-content: center; align-items: center; flex-wrap: wrap;">
                        <button class="btn btn-primary" onclick="app.testProvider(${provider.id}, this)" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">
                        🔍 测试
                    </button>
                        <button class="btn btn-success" onclick="app.syncProvider(${provider.id}, this)" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">
                        🔄 同步
                    </button>
                        <button class="btn btn-secondary" onclick="app.editProvider(${provider.id})" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">
                        ✏️ 编辑
                    </button>
                        <button class="btn btn-danger" onclick="app.deleteProvider(${provider.id}, this)" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">
                        🗑️ 删除
                    </button>
                    </div>
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
            select.innerHTML = '<option value="">🔍 全部服务商</option>';
            
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

    async loadDomains() {
        try {
            // 加载全部域名
            const response = await fetch('/api/domains/');
            const domains = await response.json();
            this.renderDomainsFromDB(domains, null);
        } catch (error) {
            this.showAlert('domains-alert', '加载域名列表失败: ' + error.message, 'error');
        }
    }

    async loadProviderDomains() {
        const providerId = document.getElementById('providerSelect').value;
        if (!providerId) {
            // 如果没有选择服务商，显示全部域名
            this.loadDomains();
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
            const message = providerId ? '该服务商下没有域名' : '暂无域名数据';
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">${message}</td></tr>`;
            return;
        }

        // 显示域名列表
        domains.forEach(domain => {
            const row = document.createElement('tr');
            const statusClass = domain.enabled ? 'enabled' : 'disabled';
            const statusText = domain.enabled ? '启用' : '禁用';
            const autoUpdateText = domain.auto_update ? '是' : '否';

            row.innerHTML = `
                <td style="text-align: center; vertical-align: middle;">${domain.name}</td>
                <td style="text-align: center; vertical-align: middle;">${domain.provider.name}</td>
                <td style="text-align: center; vertical-align: middle;"><span class="status ${statusClass}" style="display: inline-block; white-space: nowrap;">${statusText}</span></td>
                <td style="text-align: center; vertical-align: middle;">${autoUpdateText}</td>
                <td style="text-align: center; vertical-align: middle;">${new Date(domain.created_at).toLocaleDateString()}</td>
                <td style="text-align: center; vertical-align: middle;">
                    <div style="display: flex; gap: 6px; justify-content: center; align-items: center; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-primary" onclick="app.viewDomainRecords(${domain.id}, '${domain.name}')" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">解析</button>
                        <button class="btn btn-sm btn-danger" onclick="app.deleteDomain(${domain.id}, this)" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">删除</button>
                    </div>
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

        if (modal && title && form) {
        if (providerId) {
            title.textContent = '编辑服务商';
            this.loadProviderData(providerId);
        } else {
            title.textContent = '添加服务商';
            form.reset();
        }

        modal.style.display = 'block';
        } else {
            console.error('模态框元素未找到');
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
            document.getElementById('providerRegion').value = provider.region || '';
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
            region: document.getElementById('providerRegion').value || '',
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

    async toggleProvider(providerId, enabled, buttonElement = null) {
        try {
            const response = await this.apiCall(`/api/providers/${providerId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ enabled: enabled })
            }, buttonElement, '更新中...');

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

    async testProvider(providerId, buttonElement = null) {
        try {
            const response = await this.apiCall(`/api/providers/${providerId}/test`, {
                method: 'POST'
            }, buttonElement, '测试中...');
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

    async syncProvider(providerId, buttonElement = null) {
        try {
            const response = await this.apiCall(`/api/providers/${providerId}/sync`, {
                method: 'POST'
            }, buttonElement, '同步中...');

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

    async syncAllProviders(buttonElement = null) {
        if (!confirm('确定要同步所有服务商的域名吗？这可能需要一些时间。')) return;

        try {
            // 显示加载动画
            if (buttonElement) {
                this.showLoadingSpinner(buttonElement, '同步中...');
            }

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
        } finally {
            // 隐藏加载动画
            if (buttonElement) {
                this.hideLoadingSpinner(buttonElement);
            }
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

    async viewDomainRecords(domainId, domainName, page = 1, search = '') {
        try {
            // 保存当前域名ID
        this.currentDomainId = domainId;
            this.currentDomainName = domainName;
            this.currentSearch = search;

            // 构建API URL
            let url = `/api/domains/${domainId}/records?page=${page}&page_size=5`;
            if (search && search.trim()) {
                url += `&search=${encodeURIComponent(search.trim())}`;
            }

            const response = await fetch(url);
            const data = await response.json();
            
            // 创建模态框显示DNS记录
            this.showDomainRecordsModal(domainName, data, domainId);
        } catch (error) {
            this.showAlert('domains-alert', '获取DNS记录失败: ' + error.message, 'error');
        }
    }

    getCurrentPage() {
        // 从分页信息中获取当前页码
        const modal = document.getElementById('domainRecordsModal');
        if (modal) {
            const pageInfo = modal.querySelector('.pagination-buttons span');
            if (pageInfo) {
                const match = pageInfo.textContent.match(/第 (\d+) 页/);
                return match ? parseInt(match[1]) : 1;
            }
        }
        return 1;
    }

    showDomainRecordsModal(domainName, data, domainId) {
        const records = data.records;
        const pagination = data.pagination;
        const search = data.search || '';
        
        // 存储当前记录数据供编辑使用
        this.currentRecords = records;
        this.currentDomainId = domainId;
        this.currentDomainName = domainName;
        this.currentSearch = search;
        
        // 创建DNS记录显示模态框
        let recordsHtml = '';
        if (records.length === 0) {
            recordsHtml = '<p style="text-align: center; color: #666;">该域名下暂无DNS记录</p>';
        } else {
                        recordsHtml = `
                <div class="fixed-table-container">
                    <table class="fixed-table">
                        <thead style="position: sticky; top: 0; background: white; z-index: 10; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <tr>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 25%; text-align: center;">记录名称</th>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 10%; text-align: center;">类型</th>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 30%; text-align: center;">记录值</th>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 10%; text-align: center;">TTL</th>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 10%; text-align: center;">状态</th>
                                 <th style="padding: 12px 8px; border-bottom: 2px solid #ddd; width: 15%; text-align: center;">操作</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            records.forEach(record => {
                const statusClass = record.enabled ? 'enabled' : 'disabled';
                const statusText = record.enabled ? '启用' : '禁用';
                                recordsHtml += `
                    <tr style="border-bottom: 1px solid #eee;">
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; word-break: break-word; width: 25%;">${record.name}</td>
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; width: 10%;">${this.getRecordTypeText(record.type)}</td>
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; word-break: break-all; width: 30%;">${record.value}</td>
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; width: 10%;">${record.ttl}</td>
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; width: 10%;"><span class="status ${statusClass}" style="display: inline-block; white-space: nowrap;">${statusText}</span></td>
                         <td style="padding: 12px 8px; vertical-align: middle; text-align: center; width: 15%;">
                             <div style="display: flex; gap: 6px; justify-content: center; align-items: center; flex-wrap: wrap;">
                                 <button class="btn btn-sm btn-secondary" onclick="app.editDNSRecord(${record.id})" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">编辑</button>
                                 <button class="btn btn-sm btn-danger" onclick="app.deleteDNSRecord(${record.id}, this)" style="font-size: 12px; padding: 6px 12px; min-width: 60px;">删除</button>
                             </div>
                         </td>
                     </tr>
                `;
            });
            
                        recordsHtml += `
                        </tbody>
                    </table>
                    <style>
                        .fixed-table-container {
                            width: 100%;
                            overflow-x: auto;
                        }
                        .fixed-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 14px;
                            table-layout: fixed;
                        }
                        .fixed-table th {
                            font-weight: 600;
                            text-align: center;
                            background: #f8f9fa;
                            white-space: nowrap;
                        }
                        .fixed-table td {
                            text-align: center;
                            vertical-align: middle;
                        }
                        .fixed-table tr:hover {
                            background-color: #f8f9fa;
                        }
                        .btn-sm {
                            transition: all 0.2s ease;
                            white-space: nowrap;
                            border-radius: 4px;
                            font-weight: 500;
                            border: 1px solid transparent;
                        }
                        .btn-sm:hover {
                            transform: translateY(-1px);
                            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                        }
                        .btn-secondary {
                            background-color: #6c757d;
                            border-color: #6c757d;
                            color: white;
                        }
                        .btn-secondary:hover {
                            background-color: #5a6268;
                            border-color: #545b62;
                        }
                        .btn-danger {
                            background-color: #dc3545;
                            border-color: #dc3545;
                            color: white;
                        }
                        .btn-danger:hover {
                            background-color: #c82333;
                            border-color: #bd2130;
                        }
                        .pagination-buttons button:disabled {
                            opacity: 0.6;
                            cursor: not-allowed;
                            transform: none !important;
                        }
                        .pagination-buttons button:disabled:hover {
                            box-shadow: none !important;
                        }
                    </style>
                </div>
            `;
        }

        // 创建分页控件
        let paginationHtml = '';
        if (pagination && pagination.total_pages > 1) {
            paginationHtml = `
                <div class="pagination-container" style="flex-shrink: 0; border-top: 1px solid #eee; padding-top: 1rem; text-align: center; background: white;">
                    <div class="pagination-info" style="margin-bottom: 0.8rem; color: #666; font-size: 0.9rem;">
                        显示第 ${((pagination.page - 1) * pagination.page_size) + 1} - ${Math.min(pagination.page * pagination.page_size, pagination.total)} 条，共 ${pagination.total} 条记录
                    </div>
                    <div class="pagination-buttons" style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-secondary" 
                                onclick="app.viewDomainRecords(${domainId}, '${domainName}', 1, '${search}')" 
                                ${pagination.page === 1 ? 'disabled' : ''} 
                                style="min-width: 60px;">首页</button>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="app.viewDomainRecords(${domainId}, '${domainName}', ${pagination.page - 1}, '${search}')" 
                                ${!pagination.has_prev ? 'disabled' : ''} 
                                style="min-width: 70px;">上一页</button>
                        <span style="margin: 0 1rem; color: #666; white-space: nowrap;">第 ${pagination.page} 页 / 共 ${pagination.total_pages} 页</span>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="app.viewDomainRecords(${domainId}, '${domainName}', ${pagination.page + 1}, '${search}')" 
                                ${!pagination.has_next ? 'disabled' : ''} 
                                style="min-width: 70px;">下一页</button>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="app.viewDomainRecords(${domainId}, '${domainName}', ${pagination.total_pages}, '${search}')" 
                                ${pagination.page === pagination.total_pages ? 'disabled' : ''} 
                                style="min-width: 60px;">末页</button>
                    </div>
                </div>
            `;
        }

        // 检查是否已存在模态框
        const existingModal = document.getElementById('domainRecordsModal');
        if (existingModal) {
            // 如果模态框已存在，只更新内容，不重新创建
            const tableContainer = existingModal.querySelector('.records-table-container');
            const paginationContainer = existingModal.querySelector('.pagination-container');
            
            if (tableContainer) {
                tableContainer.innerHTML = recordsHtml;
            }
            if (paginationContainer) {
                paginationContainer.innerHTML = paginationHtml.replace(/<div class="pagination-container[^>]*>/, '').replace(/<\/div>$/, '');
            } else if (paginationHtml) {
                // 如果分页容器不存在但有分页内容，添加它
                existingModal.querySelector('.modal-body').insertAdjacentHTML('beforeend', paginationHtml);
            }
            return;
        }

        // 创建新的模态框（只在第一次时）
        const modalContent = `
            <div class="modal" id="domainRecordsModal" style="display: block;">
                <div class="modal-content" style="max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column;">
                    <div class="modal-header" style="flex-shrink: 0; border-bottom: 1px solid #eee; padding-bottom: 1rem;">
                        <h3>域名 ${domainName} 的解析记录</h3>
                        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <input type="text" id="dnsRecordSearch" placeholder="搜索记录名称..." 
                                       value="${search}"
                                       style="padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; width: 200px;"
                                       onkeyup="app.searchDNSRecords('${domainId}', '${domainName}')">
                                <button class="btn btn-secondary" onclick="app.clearDNSRecordSearch('${domainId}', '${domainName}')" 
                                        style="font-size: 12px; padding: 6px 12px;">清除</button>
                            </div>
                            <button class="btn btn-primary" onclick="app.showAddDNSRecordModal(${domainId}, '${domainName}')" style="font-size: 12px; padding: 6px 12px;">
                                ➕ 添加解析记录
                            </button>
                            <span class="close" onclick="app.closeDomainRecordsModal()">&times;</span>
                        </div>
                    </div>
                    <div class="modal-body" style="flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 1rem 0;">
                        <div class="records-table-container" style="flex: 1; overflow-y: auto; margin-bottom: 1rem;">
                            ${recordsHtml}
                        </div>
                        ${paginationHtml}
                    </div>
                </div>
            </div>
        `;
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalContent);
    }

    closeDomainRecordsModal() {
        const modal = document.getElementById('domainRecordsModal');
        if (modal) {
            modal.remove();
        }
        // 清理存储的数据
        this.currentDomainId = null;
        this.currentDomainName = null;
        this.currentSearch = '';
    }

    async searchDNSRecords(domainId, domainName) {
        const searchInput = document.getElementById('dnsRecordSearch');
        const searchTerm = searchInput.value.trim();
        
        // 使用后端API搜索，重置到第一页
        await this.viewDomainRecords(domainId, domainName, 1, searchTerm);
    }

    clearDNSRecordSearch(domainId, domainName) {
        const searchInput = document.getElementById('dnsRecordSearch');
        searchInput.value = '';
        // 使用后端API清除搜索，重置到第一页
        this.viewDomainRecords(domainId, domainName, 1, '');
    }


    showAddDNSRecordModal(domainId, domainName) {
        // 创建添加DNS记录的模态框
        const modalContent = `
            <div class="modal" id="addDNSRecordModal" style="display: block;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>添加解析记录 - ${domainName}</h3>
                        <span class="close" onclick="app.closeAddDNSRecordModal()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <form id="addDNSRecordForm">
                            <div class="form-group">
                                <label for="addRecordName">记录名称</label>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <input type="text" id="addRecordName" placeholder="如：www, mail, @ 等" required style="width: 200px;">
                                    <span style="color: #666; font-size: 14px;">.${domainName}</span>
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="addRecordType">记录类型</label>
                                <select id="addRecordType" required onchange="app.updateRecordValuePlaceholder()">
                                    <option value="1">A</option>
                                    <option value="2">AAAA</option>
                                    <option value="3">CNAME</option>
                                    <option value="4">MX</option>
                                    <option value="5">TXT</option>
                                    <option value="6">NS</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="addRecordValue">记录值</label>
                                <textarea id="addRecordValue" rows="3" placeholder="如：192.168.1.1, example.com 等" required style="
                                    width: 100%; 
                                    padding: 8px 12px; 
                                    border: 1px solid #ddd; 
                                    border-radius: 4px; 
                                    font-size: 14px; 
                                    font-family: inherit; 
                                    line-height: 1.4;
                                    resize: vertical;
                                    background-color: #fff;
                                    transition: border-color 0.2s ease, box-shadow 0.2s ease;
                                "></textarea>
                            </div>
                            <div class="form-group">
                                <label for="addRecordTtl">TTL</label>
                                <input type="number" id="addRecordTtl" min="60" value="3600" required>
                            </div>
                            <div class="form-group">
                                <label class="switch-container">
                                    <span>启用</span>
                                    <label class="switch">
                                        <input type="checkbox" id="addRecordEnabled" checked>
                                        <span class="slider"></span>
                                    </label>
                                </label>
                            </div>
                            <div style="text-align: right; margin-top: 2rem;">
                                <button type="button" class="btn btn-secondary" onclick="app.closeAddDNSRecordModal()">取消</button>
                                <button type="submit" class="btn btn-primary">保存</button>
                            </div>
                        </form>
                    </div>
                </div>
                <style>
                    #addRecordValue:focus {
                        outline: none;
                        border-color: #007bff;
                        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                    }
                    #addRecordValue:hover {
                        border-color: #bbb;
                    }
                    .form-group {
                        margin-bottom: 1rem;
                    }
                    .form-group label {
                        display: block;
                        margin-bottom: 0.5rem;
                        font-weight: 500;
                        color: #333;
                    }
                    .form-group input, .form-group select {
                        width: 100%;
                        padding: 8px 12px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                        font-family: inherit;
                        background-color: #fff;
                        transition: border-color 0.2s ease, box-shadow 0.2s ease;
                    }
                    .form-group input:focus, .form-group select:focus {
                        outline: none;
                        border-color: #007bff;
                        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                    }
                    .form-group input:hover, .form-group select:hover {
                        border-color: #bbb;
                    }
                </style>
            </div>
        `;
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // 绑定表单提交事件
        document.getElementById('addDNSRecordForm').addEventListener('submit', (e) => {
            this.handleAddDNSRecord(e, domainId, domainName);
        });
        
        // 初始化记录值提示
        this.updateRecordValuePlaceholder();
    }

    closeAddDNSRecordModal() {
        const modal = document.getElementById('addDNSRecordModal');
        if (modal) {
            modal.remove();
        }
    }

    showAddRecordError(message) {
        // 在添加DNS记录模态框中显示错误信息
        const modal = document.getElementById('addDNSRecordModal');
        if (!modal) return;
        
        // 查找或创建错误提示容器
        let errorContainer = modal.querySelector('.add-record-error');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'add-record-error';
            errorContainer.style.cssText = `
                margin: 1rem 0;
                padding: 0.75rem 1rem;
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                font-size: 14px;
            `;
            
            // 插入到表单之前
            const form = modal.querySelector('form');
            if (form) {
                form.parentNode.insertBefore(errorContainer, form);
            }
        }
        
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // 3秒后自动隐藏
        setTimeout(() => {
            if (errorContainer) {
                errorContainer.style.display = 'none';
            }
        }, 3000);
    }

    updateRecordValuePlaceholder() {
        const recordTypeSelect = document.getElementById('addRecordType');
        const recordValueTextarea = document.getElementById('addRecordValue');
        
        if (!recordTypeSelect || !recordValueTextarea) return;
        
        const recordType = parseInt(recordTypeSelect.value);
        let placeholder = '';
        
        switch (recordType) {
            case 1: // A
                placeholder = 'IPv4地址，如：192.168.1.1';
                break;
            case 2: // AAAA
                placeholder = 'IPv6地址，如：2001:db8::1';
                break;
            case 3: // CNAME
                placeholder = '目标域名，如：example.com';
                break;
            case 4: // MX
                placeholder = '邮件服务器域名，如：mail.example.com';
                break;
            case 5: // TXT
                placeholder = 'TXT记录值，如："v=spf1 include:_spf.google.com ~all"';
                break;
            case 6: // NS
                placeholder = '域名服务器，如：ns1.example.com';
                break;
            default:
                placeholder = '如：192.168.1.1, example.com 等';
        }
        
        recordValueTextarea.placeholder = placeholder;
    }

    async handleAddDNSRecord(e, domainId, domainName) {
        e.preventDefault();

        // 获取提交按钮并显示加载动画
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            this.showLoadingSpinner(submitButton, '添加中...');
        }

        // 构建完整的记录名
        const recordNameInput = document.getElementById('addRecordName').value.trim();
        let fullRecordName;
        
        if (recordNameInput === '@' || recordNameInput === '') {
            // @ 或空值表示主域名
            fullRecordName = domainName;
        } else {
            // 拼接子域名
            fullRecordName = `${recordNameInput}.${domainName}`;
        }

        const formData = {
            name: fullRecordName,
            type: parseInt(document.getElementById('addRecordType').value),
            value: document.getElementById('addRecordValue').value,
            ttl: parseInt(document.getElementById('addRecordTtl').value),
            enabled: document.getElementById('addRecordEnabled').checked
        };

        try {
            const response = await fetch(`/api/domains/${domainId}/records`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.showAlert('domains-alert', '添加解析记录成功', 'success');
                this.closeAddDNSRecordModal();
                // 重新加载当前页面的记录
                const currentPage = this.getCurrentPage();
                const searchInput = document.getElementById('dnsRecordSearch');
                const searchTerm = searchInput ? searchInput.value.trim() : '';
                this.viewDomainRecords(domainId, domainName, currentPage, searchTerm);
            } else {
                const error = await response.json();
                // 在添加模态框中显示错误信息
                this.showAddRecordError('添加解析记录失败: ' + error.detail);
            }
        } catch (error) {
            // 在添加模态框中显示错误信息
            this.showAddRecordError('添加解析记录失败: ' + error.message);
        } finally {
            // 隐藏加载动画
            if (submitButton) {
                this.hideLoadingSpinner(submitButton);
            }
        }
    }

    async editDNSRecord(recordId) {
        // 首先尝试从当前缓存的记录中找到对应记录
        let record = this.currentRecords?.find(r => r.id === recordId);
        
        // 如果缓存中没有，则从API获取
        if (!record && this.currentDomainId) {
            try {
                const response = await fetch(`/api/domains/${this.currentDomainId}/records?page=1&page_size=100`);
                const data = await response.json();
                record = data.records.find(r => r.id === recordId);
                // 更新缓存
                this.currentRecords = data.records;
        } catch (error) {
                console.error('获取记录失败:', error);
                this.showAlert('domains-alert', '获取记录信息失败', 'error');
                return;
            }
        }
        
        if (!record) {
            this.showAlert('domains-alert', '找不到记录信息', 'error');
            return;
        }
        
        const { name: recordName, type: recordType, value: recordValue, ttl: recordTtl, enabled: recordEnabled } = record;
        // 创建编辑DNS记录的模态框
        const modalContent = `
            <div class="modal" id="editDNSRecordModal" style="display: block;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>编辑解析记录</h3>
                        <span class="close" onclick="app.closeEditDNSRecordModal()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <form id="editDNSRecordForm">
                            <div class="form-group">
                                <label for="editRecordName">记录名称</label>
                                <input type="text" id="editRecordName" required>
                            </div>
                            <div class="form-group">
                                <label for="editRecordType">记录类型</label>
                                <select id="editRecordType" required>
                                    <option value="1">A</option>
                                    <option value="2">AAAA</option>
                                    <option value="3">CNAME</option>
                                    <option value="4">MX</option>
                                    <option value="5">TXT</option>
                                    <option value="6">NS</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="editRecordValue">记录值</label>
                                <textarea id="editRecordValue" rows="3" required style="
                                    width: 100%; 
                                    padding: 8px 12px; 
                                    border: 1px solid #ddd; 
                                    border-radius: 4px; 
                                    font-size: 14px; 
                                    font-family: inherit; 
                                    line-height: 1.4;
                                    resize: vertical;
                                    background-color: #fff;
                                    transition: border-color 0.2s ease, box-shadow 0.2s ease;
                                "></textarea>
                            </div>
                            <div class="form-group">
                                <label for="editRecordTtl">TTL</label>
                                <input type="number" id="editRecordTtl" min="60" required>
                            </div>
                            <div class="form-group">
                                <label class="switch-container">
                                    <span>启用</span>
                                    <label class="switch">
                                        <input type="checkbox" id="editRecordEnabled">
                                        <span class="slider"></span>
                                    </label>
                                </label>
                            </div>
                            <div style="text-align: right; margin-top: 2rem;">
                                <button type="button" class="btn btn-secondary" onclick="app.closeEditDNSRecordModal()">取消</button>
                                <button type="submit" class="btn btn-primary">保存</button>
                            </div>
                        </form>
                    </div>
                </div>
                <style>
                    #editRecordValue:focus {
                        outline: none;
                        border-color: #007bff;
                        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                    }
                    #editRecordValue:hover {
                        border-color: #bbb;
                    }
                    .form-group {
                        margin-bottom: 1rem;
                    }
                    .form-group label {
                        display: block;
                        margin-bottom: 0.5rem;
                        font-weight: 500;
                        color: #333;
                    }
                    .form-group input, .form-group select {
                        width: 100%;
                        padding: 8px 12px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                        font-family: inherit;
                        background-color: #fff;
                        transition: border-color 0.2s ease, box-shadow 0.2s ease;
                    }
                    .form-group input:focus, .form-group select:focus {
                        outline: none;
                        border-color: #007bff;
                        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
                    }
                    .form-group input:hover, .form-group select:hover {
                        border-color: #bbb;
                    }
                </style>
            </div>
        `;
        
        // 移除已存在的模态框
        const existingModal = document.getElementById('editDNSRecordModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // 设置表单值（避免HTML注入问题）
        document.getElementById('editRecordName').value = recordName;
        document.getElementById('editRecordType').value = recordType;
        document.getElementById('editRecordValue').value = recordValue;
        document.getElementById('editRecordTtl').value = recordTtl;
        document.getElementById('editRecordEnabled').checked = recordEnabled;
        
        // 绑定表单提交事件
        document.getElementById('editDNSRecordForm').addEventListener('submit', (e) => {
            this.handleEditDNSRecord(e, recordId);
        });
    }

    closeEditDNSRecordModal() {
        const modal = document.getElementById('editDNSRecordModal');
        if (modal) {
            modal.remove();
        }
    }

    showEditRecordError(message) {
        // 在编辑DNS记录模态框中显示错误信息
        const modal = document.getElementById('editDNSRecordModal');
        if (!modal) return;
        
        // 查找或创建错误提示容器
        let errorContainer = modal.querySelector('.edit-record-error');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'edit-record-error';
            errorContainer.style.cssText = `
                margin: 1rem 0;
                padding: 0.75rem 1rem;
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                font-size: 14px;
            `;
            
            // 插入到表单之前
            const form = modal.querySelector('form');
            if (form) {
                form.parentNode.insertBefore(errorContainer, form);
            }
        }
        
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // 3秒后自动隐藏
        setTimeout(() => {
            if (errorContainer) {
                errorContainer.style.display = 'none';
            }
        }, 3000);
    }

    showRecordsModalError(message) {
        // 在解析记录弹窗的头部显示错误信息
        const modal = document.getElementById('domainRecordsModal');
        if (!modal) return;
        
        // 查找或创建错误提示容器
        let errorContainer = modal.querySelector('.records-modal-error');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'records-modal-error';
            errorContainer.style.cssText = `
                margin: 1rem 0;
                padding: 0.75rem 1rem;
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                font-size: 14px;
            `;
            
            // 插入到模态框头部之后
            const header = modal.querySelector('.modal-header');
            if (header) {
                header.parentNode.insertBefore(errorContainer, header.nextSibling);
            }
        }
        
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // 3秒后自动隐藏
        setTimeout(() => {
            if (errorContainer) {
                errorContainer.style.display = 'none';
            }
        }, 3000);
    }

    showLoadingSpinner(button, text = '处理中...') {
        // 保存原始按钮状态
        button.dataset.originalText = button.textContent;
        button.dataset.originalDisabled = button.disabled;
        
        // 设置加载状态
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
        // 恢复原始按钮状态
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            button.disabled = button.dataset.originalDisabled === 'true';
            delete button.dataset.originalText;
            delete button.dataset.originalDisabled;
        }
    }

    // 通用API调用函数，自动处理加载动画
    async apiCall(url, options = {}, buttonElement = null, loadingText = '处理中...') {
        // 显示加载动画
        if (buttonElement) {
            this.showLoadingSpinner(buttonElement, loadingText);
        }

        try {
            const response = await fetch(url, options);
            return response;
        } finally {
            // 隐藏加载动画
            if (buttonElement) {
                this.hideLoadingSpinner(buttonElement);
            }
        }
    }

    async handleEditDNSRecord(e, recordId) {
        e.preventDefault();

        // 获取提交按钮并显示加载动画
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            this.showLoadingSpinner(submitButton, '更新中...');
        }

        const formData = {
            name: document.getElementById('editRecordName').value,
            type: parseInt(document.getElementById('editRecordType').value),
            value: document.getElementById('editRecordValue').value,
            ttl: parseInt(document.getElementById('editRecordTtl').value),
            enabled: document.getElementById('editRecordEnabled').checked
        };

        try {
            const response = await fetch(`/api/domains/records/${recordId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.showAlert('domains-alert', 'DNS记录更新成功', 'success');
                this.closeEditDNSRecordModal();
                // 重新加载当前页面的记录
                const modal = document.getElementById('domainRecordsModal');
                if (modal) {
                    // 从模态框标题中提取域名信息
                    const titleElement = modal.querySelector('h3');
                    if (titleElement) {
                        const domainName = titleElement.textContent.match(/域名 (.+) 的解析记录/)?.[1];
                        if (domainName) {
                            // 获取当前页码和搜索条件
                            const currentPage = this.getCurrentPage();
                            const searchInput = document.getElementById('dnsRecordSearch');
                            const searchTerm = searchInput ? searchInput.value.trim() : '';
                            // 重新加载当前页面
                            this.viewDomainRecords(this.currentDomainId, domainName, currentPage, searchTerm);
                        }
                    }
                }
            } else {
                const error = await response.json();
                // 在编辑模态框中显示错误信息
                this.showEditRecordError('更新失败: ' + error.detail);
            }
        } catch (error) {
            // 在编辑模态框中显示错误信息
            this.showEditRecordError('更新失败: ' + error.message);
        } finally {
            // 隐藏加载动画
            if (submitButton) {
                this.hideLoadingSpinner(submitButton);
            }
        }
    }

    async deleteDNSRecord(recordId, buttonElement = null) {
        if (!confirm('确定要删除这条解析记录吗？')) {
            return;
        }

        // 显示加载动画
        if (buttonElement) {
            this.showLoadingSpinner(buttonElement, '删除中...');
        }

        try {
            const response = await fetch(`/api/domains/records/${recordId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('domains-alert', 'DNS记录删除成功', 'success');
                // 重新加载当前页面的记录
                const modal = document.getElementById('domainRecordsModal');
                if (modal) {
                    // 从模态框标题中提取域名信息
                    const titleElement = modal.querySelector('h3');
                    if (titleElement) {
                        const domainName = titleElement.textContent.match(/域名 (.+) 的解析记录/)?.[1];
                        if (domainName) {
                            // 获取当前页码和搜索条件
                            const currentPage = this.getCurrentPage();
                            const searchInput = document.getElementById('dnsRecordSearch');
                            const searchTerm = searchInput ? searchInput.value.trim() : '';
                            // 重新加载当前页面
                            this.viewDomainRecords(this.currentDomainId, domainName, currentPage, searchTerm);
                        }
                    }
                }
            } else {
                const error = await response.json();
                // 在解析记录弹窗中显示错误信息
                this.showRecordsModalError('删除失败: ' + error.detail);
            }
        } catch (error) {
            // 在解析记录弹窗中显示错误信息
            this.showRecordsModalError('删除失败: ' + error.message);
        } finally {
            // 隐藏加载动画
            if (buttonElement) {
                this.hideLoadingSpinner(buttonElement);
            }
        }
    }

    async deleteDomain(domainId, buttonElement = null) {
        if (!confirm('确定要删除这个域名吗？这将同时删除所有相关的DNS记录。')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/domains/${domainId}`, {
                method: 'DELETE'
            }, buttonElement, '删除中...');

            if (response.ok) {
                this.showAlert('domains-alert', '域名删除成功', 'success');
                this.loadProviderDomains(); // 重新加载列表
            } else {
                const error = await response.json();
                this.showAlert('domains-alert', '删除失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('domains-alert', '删除失败: ' + error.message, 'error');
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
