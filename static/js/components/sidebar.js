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
        // 检查是否已经存在侧边栏
        const existingSidebar = document.querySelector('.sidebar');
        if (existingSidebar) {
            console.log('侧边栏已存在，移除旧的');
            existingSidebar.remove();
        }
        
        const sidebar = document.createElement('div');
        sidebar.className = 'sidebar';
        sidebar.innerHTML = `
            <div class="sidebar-header">
                <h1>🌐 DNS管理</h1>
            </div>
            <nav class="sidebar-nav">
                <a href="/dashboard" class="nav-item">
                    📊 系统概览
                </a>
                <a href="/providers" class="nav-item" data-section="providers">
                    🔧 服务商管理
                </a>
                <a href="/domains" class="nav-item" data-section="domains">
                    🌐 域名管理
                </a>
                <a href="/certificates" class="nav-item" data-section="certificates">
                    🔒 证书管理
                </a>
            </nav>
        `;
        document.body.insertBefore(sidebar, document.body.firstChild);
        console.log('侧边栏创建完成');
    }

    bindEvents() {
        // 直接为侧边栏绑定事件
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            console.log('为侧边栏绑定事件');
            sidebar.addEventListener('click', (e) => {
                console.log('侧边栏点击事件:', e.target);
                if (e.target.classList.contains('nav-item') || e.target.closest('.nav-item')) {
                    const navItem = e.target.classList.contains('nav-item') ? e.target : e.target.closest('.nav-item');
                    console.log('点击的导航项:', navItem.textContent.trim(), navItem.href);
                    
                    // 设置活跃状态
                    this.setActiveItem(navItem);
                    
                    // 检查是否有href属性（页面跳转）
                    if (navItem.href && navItem.href !== '#') {
                        console.log('执行页面跳转到:', navItem.href);
                        // 允许页面跳转，不阻止默认行为
                        return;
                    }
                    
                    // 阻止默认行为（对于没有href的项）
                    e.preventDefault();
                    
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
        } else {
            console.error('侧边栏元素未找到，无法绑定事件');
        }

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
