// إدارة حالة التطبيق
class AppState {
    constructor() {
        this.currentUser = null;
        this.currentRoom = null;
        this.onlineUsers = [];
        this.unreadCounts = {};
        this.theme = 'light';
    }
    
    // تحديث حالة المستخدم
    setCurrentUser(user) {
        this.currentUser = user;
        localStorage.setItem('current_user', JSON.stringify(user));
    }
    
    // تحديث الغرفة الحالية
    setCurrentRoom(room) {
        this.currentRoom = room;
        this.updateUnreadCount(room.id, 0);
    }
    
    // تحديث العدد غير المقروء
    updateUnreadCount(roomId, count) {
        this.unreadCounts[roomId] = count;
        this.updateBadges();
    }
    
    // تحديث الـ badges في الواجهة
    updateBadges() {
        Object.entries(this.unreadCounts).forEach(([roomId, count]) => {
            const badge = document.querySelector(`[data-room-id="${roomId}"] .unread-badge`);
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'block' : 'none';
            }
        });
    }
}

// إنشاء instance global
window.appState = new AppState();