// static/js/room.js
let currentRoomId = null;

async function loadRoomMessages(roomId) {
    try {
        const response = await fetch(`/api/messages/${roomId}`);
        const messages = await response.json();
        
        displayMessages(messages);
        currentRoomId = roomId;
        
        //标记为مقروء
        await markRoomAsRead(roomId);
        
    } catch (error) {
        console.error('Error loading messages:', error);
        showNotification('فشل تحميل الرسائل', 'error');
    }
}

async function markRoomAsRead(roomId) {
    try {
        await fetch(`/api/read/${roomId}`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Error marking as read:', error);
    }
}

// عند النقر على غرفة
document.querySelectorAll('.room-item').forEach(item => {
    item.addEventListener('click', async function() {
        const roomId = this.dataset.roomId;
        await loadRoomMessages(roomId);
    });
});