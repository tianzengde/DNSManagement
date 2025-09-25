// 侧边栏组件
class Sidebar {
    constructor() {
        this.isOpen = false;
        this.init();
    }

    init() {
        this.createSidebar();
        this.bindEvents();
    }

    createSidebar() {
        const sidebar = document.createElement('div');
        sidebar.className = 'sidebar';
        sidebar.innerHTML = `
            <div class="sidebar-header">
                <h1>🌐 DNS管理</h1>
            </div>
            <nav class="sidebar-nav">
                <a href="#" class="nav-item active" data-section="providers">
                    🔧 服务商管理
                </a>
                <a href="#" class="nav-item" data-section="domains">
                    🌐 域名管理
                </a>
                <a href="#" class="nav-item" data-section="certificates">
                    🔒 证书管理
                </a>
            </nav>
        `;
        document.body.insertBefore(sidebar, document.body.firstChild);
    }

    bindEvents() {
        // 使用事件委托来处理动态创建的导航项
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('nav-item') || e.target.closest('.nav-item')) {
                e.preventDefault();
                const navItem = e.target.classList.contains('nav-item') ? e.target : e.target.closest('.nav-item');
                this.setActiveItem(navItem);
                
                // 触发主应用的section切换
                if (window.app && typeof window.app.showSection === 'function') {
                    window.app.showSection(navItem.dataset.section);
                } else {
                    // 延迟重试
                    setTimeout(() => {
                        if (window.app && typeof window.app.showSection === 'function') {
                            window.app.showSection(navItem.dataset.section);
                        }
                    }, 100);
                }
            }
        });

        // 移动端菜单切换
        this.createMobileToggle();
    }

    setActiveItem(activeItem) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        activeItem.classList.add('active');
    }

    createMobileToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'mobile-toggle';
        toggle.innerHTML = '☰';
        toggle.style.cssText = `
            display: none;
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 2000;
            background: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            font-size: 1.2rem;
            cursor: pointer;
        `;

        toggle.addEventListener('click', () => {
            this.toggle();
        });

        document.body.appendChild(toggle);

        // 响应式处理
        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768) {
                toggle.style.display = 'block';
            } else {
                toggle.style.display = 'none';
                this.close();
            }
        });
    }

    toggle() {
        const sidebar = document.querySelector('.sidebar');
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.add('open');
        this.isOpen = true;
    }

    close() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.remove('open');
        this.isOpen = false;
    }
}

// 导出组件
window.Sidebar = Sidebar;
