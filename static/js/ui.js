// ui.js - إدارة واجهة المستخدم وتفاعلاتها

document.addEventListener('DOMContentLoaded', function() {
    // إدارة السمات
    initTheme();
    
    // إدارة القوائم المنسدلة
    initDropdowns();
    
    // إدارة النماذج
    initForms();
    
    // إدارة التنقل
    initNavigation();
    
    // إدارة التحميل
    initLoadingStates();
    
    // إدارة الإشعارات
    initNotifications();
});

// تهيئة نظام السمات
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    
    // إضافة مستمعي الأحداث لأزرار تغيير السمة
    document.querySelectorAll('[data-theme]').forEach(button => {
        button.addEventListener('click', function() {
            const theme = this.getAttribute('data-theme');
            applyTheme(theme);
            saveTheme(theme);
        });
    });
}

// تطبيق السمة المحددة
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    // تحديث الأزرار النشطة
    document.querySelectorAll('[data-theme]').forEach(button => {
        if (button.getAttribute('data-theme') === theme) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

// حفظ السمة في الخادم (إذا كان المستخدم مسجلاً)
function saveTheme(theme) {
    if (typeof currentUserId !== 'undefined' && currentUserId) {
        fetch('/api/save-theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ theme: theme })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Failed to save theme:', data.error);
            }
        })
        .catch(error => {
            console.error('Error saving theme:', error);
        });
    }
}

// تهيئة القوائم المنسدلة
function initDropdowns() {
    // إغلاق القوائم المنسدلة عند النقر خارجها
    document.addEventListener('click', function(event) {
        document.querySelectorAll('.dropdown-menu').forEach(menu => {
            if (!menu.parentElement.contains(event.target)) {
                menu.classList.remove('show');
            }
        });
    });
}

// تهيئة النماذج
function initForms() {
    // إضافة تحقق من الصحة للنماذج
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = this.querySelectorAll('[required]');
            let valid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    valid = false;
                    highlightField(field, false);
                } else {
                    highlightField(field, true);
                }
            });
            
            if (!valid) {
                e.preventDefault();
                showNotification('يرجى ملء جميع الحقول المطلوبة', 'error');
            }
        });
    });
    
    // إضافة تأثيرات للحقول
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
}

// إبراز الحقول عند التحقق
function highlightField(field, isValid) {
    if (isValid) {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
    } else {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
    }
}

// تهيئة نظام التنقل
function initNavigation() {
    // إضافة تأثيرات للروابط
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(e) {
            // إضافة تأثير تحميل للروابط الداخلية
            if (this.href && this.href.startsWith(window.location.origin)) {
                e.preventDefault();
                showLoading();
                
                setTimeout(() => {
                    window.location.href = this.href;
                }, 300);
            }
        });
    });
    
    // إضافة تأثيرات لأزرار العودة
    document.querySelectorAll('.btn-back').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.history.back();
        });
    });
}

// تهيئة حالات التحميل
function initLoadingStates() {
    // إضافة مستمع للأزرار التي تسبب تحميل
    document.querySelectorAll('.btn-loading').forEach(button => {
        button.addEventListener('click', function() {
            this.setAttribute('data-original-text', this.innerHTML);
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> جاري التحميل...';
            this.disabled = true;
        });
    });
}

// إظهار حالة التحميل
function showLoading() {
    const loader = document.createElement('div');
    loader.className = 'page-loader';
    loader.innerHTML = `
        <div class="loader-overlay"></div>
        <div class="loader-content">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">جاري التحميل...</span>
            </div>
            <p>جاري التحميل...</p>
        </div>
    `;
    document.body.appendChild(loader);
}

// إخفاء حالة التحميل
function hideLoading() {
    const loader = document.querySelector('.page-loader');
    if (loader) {
        loader.remove();
    }
}

// تهيئة نظام الإشعارات
function initNotifications() {
    // إضافة مستمع لإغلاق الإشعارات
    document.querySelectorAll('.alert .btn-close').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').remove();
        });
    });
    
    // إغلاق تلقائي للإشعارات بعد 5 ثوان
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
}

// إظهار إشعار
function showNotification(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts-container') || createAlertsContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // إغلاق تلقائي بعد 5 ثوان
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// إنشاء حاوية للإشعارات إذا لم تكن موجودة
function createAlertsContainer() {
    const container = document.createElement('div');
    container.id = 'alerts-container';
    container.className = 'position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// نسخ النص إلى الحافظة
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('تم نسخ النص إلى الحافظة', 'success');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showNotification('فشل نسخ النص', 'error');
    });
}

// التمرير إلى عنصر معين
function scrollToElement(elementId, offset = 20) {
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

// إدارة حالة الاتصال
function updateConnectionStatus(isOnline) {
    const statusElement = document.getElementById('connection-status') || createConnectionStatusElement();
    
    if (isOnline) {
        statusElement.className = 'connection-status online';
        statusElement.innerHTML = '<i class="fas fa-wifi"></i> متصل';
    } else {
        statusElement.className = 'connection-status offline';
        statusElement.innerHTML = '<i class="fas fa-wifi-slash"></i> غير متصل';
    }
}

// إنشاء عنصر حالة الاتصال إذا لم يكن موجوداً
function createConnectionStatusElement() {
    const statusElement = document.createElement('div');
    statusElement.id = 'connection-status';
    statusElement.className = 'connection-status';
    document.body.appendChild(statusElement);
    return statusElement;
}

// التحقق من حالة الاتصال
function checkConnection() {
    const isOnline = navigator.onLine;
    updateConnectionStatus(isOnline);
    
    // إضافة مستمعين لتغير حالة الاتصال
    window.addEventListener('online', () => updateConnectionStatus(true));
    window.addEventListener('offline', () => updateConnectionStatus(false));
}

// تهيئة كل شيء عند تحميل الصفحة
window.addEventListener('load', function() {
    // إخفاء حالة التحميل إذا كانت معروضة
    hideLoading();
    
    // التحقق من حالة الاتصال
    checkConnection();
    
    // إضافة تأثيرات للصور
    initImages();
    
    // إضافة تأثيرات للبطاقات
    initCards();
});

// تهيئة تأثيرات الصور
function initImages() {
    document.querySelectorAll('img').forEach(img => {
        // إضافة تأثير تحميل للصور
        if (!img.complete) {
            img.classList.add('loading');
            img.addEventListener('load', function() {
                this.classList.remove('loading');
                this.classList.add('loaded');
            });
            img.addEventListener('error', function() {
                this.classList.remove('loading');
                this.classList.add('error');
            });
        }
    });
}

// تهيئة تأثيرات البطاقات
function initCards() {
    document.querySelectorAll('.card-hover').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('hover');
        });
        card.addEventListener('mouseleave', function() {
            this.classList.remove('hover');
        });
    });
}