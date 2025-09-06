// static/js/app.js - إدارة حالة التطبيق
class ChatApp {
    constructor() {
        this.currentUser = null;
        this.currentRoom = null;
        this.socket = null;
        this.init();
    }
    
    async init() {
        await this.loadCurrentUser();
        this.setupSocketConnection();
        this.loadInitialData();
    }
    
    async loadCurrentUser() {
        try {
            const response = await fetch('/api/user/me');
            this.currentUser = await response.json();
        } catch (error) {
            console.error('Error loading user:', error);
        }
    }
    
    setupSocketConnection() {
        this.socket = io();
        
        this.socket.on('new_message', (message) => {
            this.addMessageToChat(message);
        });
        
        this.socket.on('user_online', (user) => {
            this.updateOnlineStatus(user.id, true);
        });
        
        this.socket.on('user_offline', (userId) => {
            this.updateOnlineStatus(userId, false);
        });
    }
    
    async loadInitialData() {
        await this.loadOnlineUsers();
        await this.loadUserRooms();
    }
    
    async loadOnlineUsers() {
        try {
            const response = await fetch('/api/users/online');
            const onlineUsers = await response.json();
            this.updateOnlineUsersList(onlineUsers);
        } catch (error) {
            console.error('Error loading online users:', error);
        }
    }
    
    async loadUserRooms() {
        try {
            const response = await fetch('/api/rooms');
            const rooms = await response.json();
            this.displayUserRooms(rooms);
        } catch (error) {
            console.error('Error loading rooms:', error);
        }
    }
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});