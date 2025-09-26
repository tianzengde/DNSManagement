// 共享工具函数

// 显示警告信息
function showAlert(containerId, message, type) {
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

// 显示加载动画
function showLoadingSpinner(button, text = '处理中...') {
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

// 隐藏加载动画
function hideLoadingSpinner(button) {
    if (!button) return;
    
    if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
        button.disabled = button.dataset.originalDisabled === 'true';
        delete button.dataset.originalText;
        delete button.dataset.originalDisabled;
    }
}

// 通用API调用函数，自动处理加载动画
async function apiCall(url, options = {}, buttonElement = null, loadingText = '处理中...') {
    if (buttonElement) {
        showLoadingSpinner(buttonElement, loadingText);
    }

    try {
        const response = await fetch(url, options);
        return response;
    } finally {
        if (buttonElement) {
            hideLoadingSpinner(buttonElement);
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
