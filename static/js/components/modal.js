// 模态框组件
class Modal {
    constructor(id, title, content) {
        this.id = id;
        this.title = title;
        this.content = content;
        this.isOpen = false;
        this.create();
    }

    create() {
        const modal = document.createElement('div');
        modal.id = this.id;
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="${this.id}Title">${this.title}</h3>
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body">
                    ${this.content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.bindEvents();
    }

    bindEvents() {
        const modal = document.getElementById(this.id);
        const closeBtn = modal.querySelector('.close');

        closeBtn.addEventListener('click', () => {
            this.close();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close();
            }
        });
    }

    open() {
        const modal = document.getElementById(this.id);
        modal.style.display = 'block';
        this.isOpen = true;
        
        // 添加动画效果
        setTimeout(() => {
            modal.classList.add('fade-in');
        }, 10);
    }

    close() {
        const modal = document.getElementById(this.id);
        modal.style.display = 'none';
        this.isOpen = false;
        modal.classList.remove('fade-in');
    }

    updateTitle(title) {
        const titleElement = document.getElementById(`${this.id}Title`);
        if (titleElement) {
            titleElement.textContent = title;
        }
    }

    updateContent(content) {
        const bodyElement = document.querySelector(`#${this.id} .modal-body`);
        if (bodyElement) {
            bodyElement.innerHTML = content;
        }
    }

    destroy() {
        const modal = document.getElementById(this.id);
        if (modal) {
            modal.remove();
        }
    }
}

// 工具函数
class ModalUtils {
    static createProviderModal() {
        const content = `
            <form id="providerForm">
                <div class="form-group">
                    <label for="providerName">服务商名称</label>
                    <input type="text" id="providerName" required>
                </div>
                <div class="form-group">
                    <label for="providerType">服务商类型</label>
                    <select id="providerType" required>
                        <option value="">请选择</option>
                        <option value="1">华为云</option>
                        <option value="2">阿里云</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="providerAccessKey">访问密钥</label>
                    <input type="text" id="providerAccessKey" required>
                </div>
                <div class="form-group">
                    <label for="providerSecretKey">秘密密钥</label>
                    <input type="password" id="providerSecretKey" required>
                </div>
                <div class="form-group">
                    <label class="switch-container">
                        <span>启用</span>
                        <label class="switch">
                            <input type="checkbox" id="providerEnabled" checked>
                            <span class="slider"></span>
                        </label>
                    </label>
                </div>
                <div style="text-align: right; margin-top: 2rem;">
                    <button type="button" class="btn btn-secondary" onclick="app.closeProviderModal()">取消</button>
                    <button type="submit" class="btn btn-primary">保存</button>
                </div>
            </form>
        `;

        return new Modal('providerModal', '添加服务商', content);
    }

    static createDomainModal() {
        const content = `
            <form id="domainForm">
                <div class="form-group">
                    <label for="domainName">域名</label>
                    <input type="text" id="domainName" placeholder="example.com" required>
                </div>
                <div class="form-group">
                    <label for="domainProvider">服务商</label>
                    <select id="domainProvider" required>
                        <option value="">请选择</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="switch-container">
                        <span>启用</span>
                        <label class="switch">
                            <input type="checkbox" id="domainEnabled" checked>
                            <span class="slider"></span>
                        </label>
                    </label>
                </div>
                <div class="form-group">
                    <label class="switch-container">
                        <span>自动更新</span>
                        <label class="switch">
                            <input type="checkbox" id="domainAutoUpdate">
                            <span class="slider"></span>
                        </label>
                    </label>
                </div>
                <div style="text-align: right; margin-top: 2rem;">
                    <button type="button" class="btn btn-secondary" onclick="app.closeDomainModal()">取消</button>
                    <button type="submit" class="btn btn-primary">保存</button>
                </div>
            </form>
        `;

        return new Modal('domainModal', '添加域名', content);
    }
}

// 导出组件
window.Modal = Modal;
window.ModalUtils = ModalUtils;
