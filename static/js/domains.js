/**
 * 域名管理页面管理器
 */
class DomainsManager {
    constructor() {
        this.currentDomainId = null;
        this.currentDomainName = null;
        this.currentSearch = '';
        this.currentRecords = [];
        this.init();
    }

    init() {
        this.createModals();
        this.bindEvents();
        this.loadProviderSelect();
        this.loadDomains();
    }

    createModals() {
        // DNS记录模态框将在需要时动态创建
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
    }

    async loadProviderSelect() {
        try {
            const response = await fetch('/api/providers/');
            const providers = await response.json();
            
            const select = document.getElementById('providerSelect');
            if (!select) return;
            
            select.innerHTML = '<option value="">🔍 选择服务商查看域名</option>';
            
            providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.id;
                option.textContent = provider.name;
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

    renderDomainsFromDB(domains, providerId) {
        const tbody = document.getElementById('domains-table');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (domains.length === 0) {
            const message = providerId ? '该服务商下没有域名' : '暂无域名数据';
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">${message}</td></tr>`;
            return;
        }

        domains.forEach(domain => {
            const row = document.createElement('tr');
            const providerName = domain.provider ? domain.provider.name : '未知';
            const statusClass = domain.enabled ? 'enabled' : 'disabled';
            const statusText = domain.enabled ? '启用' : '禁用';
            const autoUpdateText = domain.auto_update ? '是' : '否';
            
            row.innerHTML = `
                <td style="text-align: center; vertical-align: middle;">${domain.name}</td>
                <td style="text-align: center; vertical-align: middle;">${providerName}</td>
                <td style="text-align: center; vertical-align: middle;">
                    <span class="status ${statusClass}" style="display: inline-block; white-space: nowrap;">${statusText}</span>
                </td>
                <td style="text-align: center; vertical-align: middle;">${autoUpdateText}</td>
                <td style="text-align: center; vertical-align: middle;">${new Date(domain.created_at).toLocaleDateString()}</td>
                <td style="text-align: center;">
                    <button class="btn btn-primary" onclick="domainsApp.viewDomainRecords(${domain.id}, '${domain.name}')">
                        🔍 解析
                    </button>
                    <button class="btn btn-danger" onclick="domainsApp.deleteDomain(${domain.id}, this)">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

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
                             <button class="btn btn-secondary" onclick="domainsApp.editDNSRecord(${record.id})">
                                 ✏️ 编辑
                             </button>
                             <button class="btn btn-danger" onclick="domainsApp.deleteDNSRecord(${record.id}, this)">
                                 🗑️ 删除
                             </button>
                         </td>
                    </tr>
                `;
            });
            
            recordsHtml += `
                        </tbody>
                    </table>
                </div>
            `;
        }

        // 分页HTML
        let paginationHtml = '';
        if (pagination.total_pages > 1) {
            paginationHtml = `
                <div class="pagination-container" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #eee;">
                    <div class="pagination-buttons" style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-secondary" 
                                onclick="domainsApp.viewDomainRecords(${domainId}, '${domainName}', 1, '${search}')" 
                                ${pagination.page === 1 ? 'disabled' : ''} 
                                style="min-width: 60px;">首页</button>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="domainsApp.viewDomainRecords(${domainId}, '${domainName}', ${pagination.page - 1}, '${search}')" 
                                ${!pagination.has_prev ? 'disabled' : ''} 
                                style="min-width: 70px;">上一页</button>
                        <span style="margin: 0 1rem; color: #666; white-space: nowrap;">第 ${pagination.page} 页 / 共 ${pagination.total_pages} 页</span>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="domainsApp.viewDomainRecords(${domainId}, '${domainName}', ${pagination.page + 1}, '${search}')" 
                                ${!pagination.has_next ? 'disabled' : ''} 
                                style="min-width: 70px;">下一页</button>
                        <button class="btn btn-sm btn-secondary" 
                                onclick="domainsApp.viewDomainRecords(${domainId}, '${domainName}', ${pagination.total_pages}, '${search}')" 
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
                                       onkeyup="domainsApp.searchDNSRecords('${domainId}', '${domainName}')">
                                <button class="btn btn-secondary" onclick="domainsApp.clearDNSRecordSearch('${domainId}', '${domainName}')">
                                    清除
                                </button>
                            </div>
                            <button class="btn btn-primary" onclick="domainsApp.showAddDNSRecordModal(${domainId}, '${domainName}')">
                                ➕ 添加解析记录
                            </button>
                            <span class="close" onclick="domainsApp.closeDomainRecordsModal()">&times;</span>
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
                        <span class="close" onclick="domainsApp.closeAddDNSRecordModal()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <form id="addDNSRecordForm">
                            <div class="form-group">
                                <label for="addRecordName">记录名称</label>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <input type="text" id="addRecordName" placeholder="如：www, mail, @ 等" required 
                                           style="flex: 0 0 56%;" oninput="domainsApp.updateRecordNamePreview('${domainName}')">
                                    <span id="recordNamePreview" style="color: #000; font-weight: 500; flex: 0 0 44%; padding-left: 0.5rem;"></span>
                                </div>
                                <small class="form-text">只需输入子域名前缀，完整域名将自动生成</small>
                            </div>
                            <div class="form-group">
                                <label for="addRecordType">记录类型</label>
                                <select id="addRecordType" required onchange="domainsApp.updateRecordValuePlaceholder()">
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
                                <textarea id="addRecordValue" rows="3" placeholder="如：192.168.1.1, example.com 等" required class="form-textarea"></textarea>
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
                                <button type="button" class="btn btn-secondary" onclick="domainsApp.closeAddDNSRecordModal()">取消</button>
                                <button type="submit" class="btn btn-primary">添加</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // 初始化预览
        this.updateRecordNamePreview(domainName);
        this.updateRecordValuePlaceholder();
        
        // 绑定表单提交事件
        const form = document.getElementById('addDNSRecordForm');
        form.addEventListener('submit', (e) => this.handleAddDNSRecord(e, domainId, domainName));
    }

    updateRecordNamePreview(domainName) {
        const recordNameInput = document.getElementById('addRecordName');
        const recordNamePreview = document.getElementById('recordNamePreview');
        
        if (!recordNameInput || !recordNamePreview) return;
        
        const inputValue = recordNameInput.value.trim();
        
        // 始终显示主域名，与DDNS弹窗保持一致
        recordNamePreview.textContent = `.${domainName}`;
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
                placeholder = 'TXT记录的内容应该在""内，如："v=spf1 include:_spf.google.com ~all"';
                break;
            case 6: // NS
                placeholder = '域名服务器，如：ns1.example.com';
                break;
            default:
                placeholder = '如：192.168.1.1, example.com 等';
                break;
        }
        
        recordValueTextarea.placeholder = placeholder;
    }

    async handleAddDNSRecord(e, domainId, domainName) {
        e.preventDefault();
        
        const submitButton = e.target.querySelector('button[type="submit"]');
        this.showLoadingSpinner(submitButton, '添加中...');
        
        const nameInput = document.getElementById('addRecordName');
        const subdomain = nameInput.value.trim();
        const fullDomain = subdomain ? `${subdomain}.${domainName}` : domainName;
        
        const formData = {
            name: fullDomain,
            type: parseInt(document.getElementById('addRecordType').value),
            value: document.getElementById('addRecordValue').value,
            ttl: parseInt(document.getElementById('addRecordTtl').value),
            enabled: document.getElementById('addRecordEnabled').checked,
            domain_id: domainId
        };

        try {
            const response = await fetch(`/api/domains/${domainId}/records`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.closeAddDNSRecordModal();
                // 重新加载DNS记录列表，保持当前页面和搜索
                const currentPage = this.getCurrentPage();
                const searchInput = document.getElementById('dnsRecordSearch');
                const searchTerm = searchInput ? searchInput.value.trim() : '';
                this.viewDomainRecords(domainId, domainName, currentPage, searchTerm);
            } else {
                const error = await response.json();
                this.showAddRecordError('添加解析记录失败: ' + error.detail);
            }
        } catch (error) {
            this.showAddRecordError('添加解析记录失败: ' + error.message);
        } finally {
            this.hideLoadingSpinner(submitButton);
        }
    }

    closeAddDNSRecordModal() {
        const modal = document.getElementById('addDNSRecordModal');
        if (modal) {
            modal.remove();
        }
    }

    showAddRecordError(message) {
        const alertContainer = document.getElementById('add-record-alert');
        if (alertContainer) {
            alertContainer.innerHTML = `<div class="alert alert-error">${message}</div>`;
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 5000);
        }
    }

    async editDNSRecord(recordId) {
        // 从缓存中查找记录
        let record = this.currentRecords.find(r => r.id === recordId);
        
        // 如果缓存中没有，则从API获取
        if (!record && this.currentDomainId) {
            try {
                const response = await fetch(`/api/domains/${this.currentDomainId}/records?page=1&page_size=100`);
                const data = await response.json();
                record = data.records.find(r => r.id === recordId);
                // 更新缓存
                this.currentRecords = data.records;
            } catch (error) {
                this.showAlert('domains-alert', '获取记录信息失败: ' + error.message, 'error');
                return;
            }
        }
        
        if (!record) {
            this.showAlert('domains-alert', '找不到指定的DNS记录', 'error');
            return;
        }
        
        // 创建编辑DNS记录的模态框
        const modal = document.createElement('div');
        modal.id = 'editDNSRecordModal';
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h3>编辑DNS记录</h3>
                    <span class="close" onclick="domainsApp.closeEditDNSRecordModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div id="edit-record-alert"></div>
                    <form id="editDNSRecordForm">
                        <div class="form-group">
                            <label for="editRecordName">记录名称</label>
                            <input type="text" id="editRecordName" value="${record.name}" required>
                        </div>
                        <div class="form-group">
                            <label for="editRecordType">记录类型</label>
                            <select id="editRecordType" onchange="domainsApp.updateEditRecordValuePlaceholder()">
                                <option value="1" ${record.type === 1 ? 'selected' : ''}>A</option>
                                <option value="2" ${record.type === 2 ? 'selected' : ''}>AAAA</option>
                                <option value="3" ${record.type === 3 ? 'selected' : ''}>CNAME</option>
                                <option value="4" ${record.type === 4 ? 'selected' : ''}>MX</option>
                                <option value="5" ${record.type === 5 ? 'selected' : ''}>TXT</option>
                                <option value="6" ${record.type === 6 ? 'selected' : ''}>NS</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="editRecordValue">记录值</label>
                            <input type="text" id="editRecordValue" value="${record.value}" required>
                        </div>
                        <div class="form-group">
                            <label for="editRecordTTL">TTL (秒)</label>
                            <input type="number" id="editRecordTTL" value="${record.ttl}" min="60" max="86400">
                        </div>
                        <div class="form-group">
                            <label for="editRecordPriority">优先级 (仅MX记录)</label>
                            <input type="number" id="editRecordPriority" value="${record.priority || 10}" min="0" max="65535">
                        </div>
                        <div class="form-group">
                            <label class="switch-container">
                                <span>启用</span>
                                <label class="switch">
                                    <input type="checkbox" id="editRecordEnabled" ${record.enabled ? 'checked' : ''}>
                                    <span class="slider"></span>
                                </label>
                            </label>
                        </div>
                        <div style="text-align: right; margin-top: 2rem;">
                            <button type="button" class="btn btn-secondary" onclick="domainsApp.closeEditDNSRecordModal()">取消</button>
                            <button type="submit" class="btn btn-primary">保存</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 初始化优先级字段显示状态
        this.updateEditRecordValuePlaceholder();
        
        // 绑定表单提交事件
        const form = document.getElementById('editDNSRecordForm');
        form.addEventListener('submit', (e) => this.handleEditDNSRecord(e, recordId));
    }

    updateEditRecordValuePlaceholder() {
        const typeSelect = document.getElementById('editRecordType');
        const valueInput = document.getElementById('editRecordValue');
        const priorityInput = document.getElementById('editRecordPriority');
        
        if (!typeSelect || !valueInput) return;
        
        const type = parseInt(typeSelect.value);
        
        // 显示/隐藏优先级字段
        if (priorityInput) {
            const priorityGroup = priorityInput.closest('.form-group');
            if (priorityGroup) {
                priorityGroup.style.display = type === 4 ? 'block' : 'none';
            }
        }
    }

    async handleEditDNSRecord(e, recordId) {
        e.preventDefault();
        
        const submitButton = e.target.querySelector('button[type="submit"]');
        this.showLoadingSpinner(submitButton, '保存中...');
        
        const formData = {
            name: document.getElementById('editRecordName').value,
            type: parseInt(document.getElementById('editRecordType').value),
            value: document.getElementById('editRecordValue').value,
            ttl: parseInt(document.getElementById('editRecordTTL').value),
            priority: document.getElementById('editRecordPriority').value || null,
            enabled: document.getElementById('editRecordEnabled').checked
        };

        try {
            const response = await fetch(`/api/domains/records/${recordId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                this.closeEditDNSRecordModal();
                // 重新加载DNS记录列表，保持当前页面和搜索
                const currentPage = this.getCurrentPage();
                const domainName = this.currentDomainName;
                if (domainName) {
                    const searchInput = document.getElementById('dnsRecordSearch');
                    const searchTerm = searchInput ? searchInput.value.trim() : '';
                    this.viewDomainRecords(this.currentDomainId, domainName, currentPage, searchTerm);
                }
            } else {
                const error = await response.json();
                this.showEditRecordError('更新解析记录失败: ' + error.detail);
            }
        } catch (error) {
            this.showEditRecordError('更新解析记录失败: ' + error.message);
        } finally {
            this.hideLoadingSpinner(submitButton);
        }
    }

    closeEditDNSRecordModal() {
        const modal = document.getElementById('editDNSRecordModal');
        if (modal) {
            modal.remove();
        }
    }

    showEditRecordError(message) {
        const alertContainer = document.getElementById('edit-record-alert');
        if (alertContainer) {
            alertContainer.innerHTML = `<div class="alert alert-error">${message}</div>`;
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 5000);
        }
    }

    async deleteDNSRecord(recordId, buttonElement = null) {
        if (!confirm('确定要删除这条DNS记录吗？')) {
            return;
        }

        try {
            const response = await this.apiCall(`/api/domains/records/${recordId}`, {
                method: 'DELETE'
            }, buttonElement, '删除中...');

            if (response.ok) {
                // 重新加载DNS记录列表，保持当前页面和搜索
                const currentPage = this.getCurrentPage();
                const domainName = this.currentDomainName;
                if (domainName) {
                    const searchInput = document.getElementById('dnsRecordSearch');
                    const searchTerm = searchInput ? searchInput.value.trim() : '';
                    this.viewDomainRecords(this.currentDomainId, domainName, currentPage, searchTerm);
                }
            } else {
                const error = await response.json();
                this.showAlert('domains-alert', '删除失败: ' + error.detail, 'error');
            }
        } catch (error) {
            this.showAlert('domains-alert', '删除失败: ' + error.message, 'error');
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

    getCurrentPage() {
        // 从分页按钮中提取当前页码
        const paginationSpan = document.querySelector('.pagination-buttons span');
        if (paginationSpan) {
            const match = paginationSpan.textContent.match(/第 (\d+) 页/);
            return match ? parseInt(match[1]) : 1;
        }
        return 1;
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

// 导出 DomainsManager 类
window.DomainsManager = DomainsManager;

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;
    
    // 初始化域名管理器
    window.domainsApp = new DomainsManager();
    
    // 创建侧边栏
    const sidebar = new Sidebar();
    
    // 延迟设置域名管理为当前活跃页面
    setTimeout(() => {
        const domainsNavItem = document.querySelector('[href="/domains"]');
        if (domainsNavItem) {
            // 清除其他活跃状态
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            // 设置当前页面为活跃
            domainsNavItem.classList.add('active');
        }
    }, 100);
});
