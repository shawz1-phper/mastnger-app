// static/js/online-users.js
async function loadOnlineUsers() {
    try {
        const response = await fetch('/api/users/online');
        const onlineUsers = await response.json();
        
        const onlineList = document.getElementById('online-users-list');
        onlineList.innerHTML = '';
        
        onlineUsers.forEach(user => {
            const userElement = document.createElement('div');
            userElement.className = 'online-user';
            userElement.innerHTML = `
                <img src="/static/img/avatars/${user.avatar_url}" 
                     alt="${user.username}" class="user-avatar-sm">
                <span>${user.username}</span>
                <div class="online-indicator"></div>
            `;
            onlineList.appendChild(userElement);
        });
    } catch (error) {
        console.error('Error loading online users:', error);
    }
}

// تحديث قائمة المتصلين كل 30 ثانية
setInterval(loadOnlineUsers, 30000);

// تحميل أولي
document.addEventListener('DOMContentLoaded', loadOnlineUsers);