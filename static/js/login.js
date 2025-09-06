// تسجيل الدخول
async function loginUser(email, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const user = await response.json();
            // حفظ token أو إدارة session
            localStorage.setItem('auth_token', user.token);
            localStorage.setItem('user_id', user.id);
            window.location.href = '/dashboard';
        } else {
            const error = await response.json();
            showNotification(error.message, 'error');
        }
    } catch (error) {
        showNotification('حدث خطأ في الاتصال', 'error');
    }
}

// التسجيل
async function registerUser(username, email, password) {
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password })
        });

        if (response.ok) {
            showNotification('تم إنشاء الحساب بنجاح', 'success');
            return true;
        } else {
            const error = await response.json();
            showNotification(error.message, 'error');
            return false;
        }
    } catch (error) {
        showNotification('حدث خطأ في الاتصال', 'error');
        return false;
    }
}