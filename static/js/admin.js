// لوحة تحكم المشرف
async function loadAdminDashboard() {
    try {
        const [statsResponse, usersResponse] = await Promise.all([
            fetch('/api/admin/stats'),
            fetch('/api/admin/users?page=1')
        ]);
        
        const stats = await statsResponse.json();
        const usersData = await usersResponse.json();
        
        updateStatsDisplay(stats);
        displayUsersTable(usersData.users);
        setupPagination(usersData.pagination);
        
    } catch (error) {
        console.error('Error loading admin dashboard:', error);
    }
}

function updateStatsDisplay(stats) {
    document.getElementById('total-users').textContent = stats.total_users;
    document.getElementById('online-users').textContent = stats.online_users;
    document.getElementById('total-messages').textContent = stats.total_messages;
    document.getElementById('active-today').textContent = stats.active_today;
}

// إدارة المستخدمين
async function deleteUser(userId) {
    if (confirm('هل أنت متأكد من حذف هذا المستخدم؟')) {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showNotification('تم حذف المستخدم بنجاح', 'success');
                loadAdminDashboard(); // إعادة تحميل البيانات
            }
        } catch (error) {
            showNotification('حدث خطأ أثناء الحذف', 'error');
        }
    }
}