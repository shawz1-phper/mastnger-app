// ui.js - مكتبة مساعدة لواجهة المستخدم
class UIManager {
    constructor() {
        this.notificationTimeout = null;
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupEventListeners();
        console.log('🎨 UI Manager initialized');
    }

    // ==================== الإشعارات والتنبيهات ====================
    
    showNotification(message, type = 'info', duration = 5000) {
        // إخفاء أي إشعار سابق
        this.hideNotification();
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${this.getNotificationIcon(type)} me-2"></i>
                <span>${message}</span>
                <button class="btn-close btn-close-white ms-auto" onclick="uiManager.hideNotification()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // إخفاء تلقائي بعد المدة المحددة
        this.notificationTimeout = setTimeout(() => {
            this.hideNotification();
        }, duration);
        
        return notification;
    }

    hideNotification() {
        const notification = document.querySelector('.notification');
        if (notification) {
            notification.remove();
        }
        if (this.notificationTimeout) {
            clearTimeout(this.notificationTimeout);
        }
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    }

    // ==================== إدارة السمات ====================
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
        
        // تحديث الأزرار النشطة
        document.querySelectorAll('[data-theme]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
        });
        
        this.showNotification(`تم التغيير إلى السمة ${theme === 'light' ? 'الفاتحة' : 'المظلمة'}`, 'success', 2000);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
    }

    // ==================== إدارة التحميل ====================
    
    showLoader(text = 'جاري التحميل...') {
        this.hideLoader();
        
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <p>${text}</p>
            </div>
        `;
        
        document.body.appendChild(loader);
        document.body.style.overflow = 'hidden';
    }

    hideLoader() {
        const loader = document.querySelector('.loading-overlay');
        if (loader) {
            loader.remove();
        }
        document.body.style.overflow = '';
    }

    // ==================== إدارة النماذج ====================
    
    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('[required]');
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.highlightField(input, false);
                isValid = false;
            } else {
                this.highlightField(input, true);
            }
        });
        
        return isValid;
    }

    highlightField(field, isValid) {
        field.classList.remove('is-valid', 'is-invalid');
        field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        
        // إظهار رسالة الخطأ إذا لزم الأمر
        if (!isValid) {
            this.showTooltip(field, 'هذا الحقل مطلوب');
        }
    }

    resetForm(form) {
        form.reset();
        form.querySelectorAll('.is-valid, .is-invalid').forEach(field => {
            field.classList.remove('is-valid', 'is-invalid');
        });
    }

    // ==================== الأدوات المساعدة ====================
    
    showTooltip(element, message) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = message;
        
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.bottom + 5}px`;
        tooltip.style.left = `${rect.left}px`;
        
        document.body.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 3000);
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('تم نسخ النص إلى الحافظة', 'success');
        }).catch(err => {
            this.showNotification('فشل نسخ النص', 'error');
        });
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'الآن';
        if (diff < 3600000) return `منذ ${Math.floor(diff / 60000)} دقيقة`;
        if (diff < 86400000) return `منذ ${Math.floor(diff / 3600000)} ساعة`;
        if (diff < 604800000) return `منذ ${Math.floor(diff / 86400000)} يوم`;
        
        return date.toLocaleDateString('ar-EG');
    }

    // ==================== إدارة العناصر ====================
    
    toggleElement(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }

    scrollToElement(elementId, offset = 20) {
        const element = document.getElementById(elementId);
        if (element) {
            const elementPosition = element.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - offset;
            
            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    }

    // ==================== event listeners ====================
    
    setupEventListeners() {
        // theme toggle
        document.querySelectorAll('[data-theme]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const theme = btn.getAttribute('data-theme');
                this.applyTheme(theme);
            });
        });
        
        // tooltips
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            el.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.getAttribute('data-tooltip'));
            });
        });
    }
}

// إنشاء instance global
window.uiManager = new UIManager();

// دوال مساعدة global للاستخدام السريع
window.showNotification = (message, type, duration) => uiManager.showNotification(message, type, duration);
window.hideNotification = () => uiManager.hideNotification();
window.showLoader = (text) => uiManager.showLoader(text);
window.hideLoader = () => uiManager.hideLoader();
window.toggleTheme = () => uiManager.toggleTheme();