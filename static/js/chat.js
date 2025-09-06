document.addEventListener('DOMContentLoaded', function() {
    // الاتصال بالسوكيت
    const socket = io();
    
    // عناصر واجهة المستخدم
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const roomName = document.getElementById('room-name').value;
    const isPrivate = document.getElementById('is-private').value === 'true';
    const recipientId = document.getElementById('recipient-id').value;
    
    // الانضمام إلى الغرفة
    if (roomName && !isPrivate) {
        socket.emit('join', { room: roomName });
    } else if (isPrivate && recipientId) {
        const chatKey = [currentUserId, recipientId].sort().join('_');
        socket.emit('join', { room: chatKey });
    }
    
    // إرسال الرسالة
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        if (isPrivate && recipientId) {
            socket.emit('message', {
                message: message,
                private: true,
                recipient: recipientId
            });
        } else {
            socket.emit('message', {
                message: message,
                room: roomName
            });
        }
        
        messageInput.value = '';
        stopTyping();
    });
    
    // استقبال الرسائل
    socket.on('message', function(data) {
        addMessage(data, false);
    });
    
    socket.on('private_message', function(data) {
        addMessage(data, false);
    });
    
    socket.on('status', function(data) {
        addMessage(data, true);
    });
    
    // مؤشر الكتابة
    let typing = false;
    let typingTimer;
    
    messageInput.addEventListener('input', function() {
        if (!typing) {
            typing = true;
            if (isPrivate && recipientId) {
                socket.emit('typing', {
                    is_typing: true,
                    private: true,
                    recipient: recipientId
                });
            } else {
                socket.emit('typing', {
                    is_typing: true,
                    room: roomName
                });
            }
        }
        
        clearTimeout(typingTimer);
        typingTimer = setTimeout(stopTyping, 2000);
    });
    
    socket.on('typing', function(data) {
        if (data.is_typing) {
            typingIndicator.textContent = `${data.username} يكتب الآن...`;
            typingIndicator.style.display = 'block';
        } else {
            typingIndicator.style.display = 'none';
        }
    });
    
    function stopTyping() {
        typing = false;
        if (isPrivate && recipientId) {
            socket.emit('typing', {
                is_typing: false,
                private: true,
                recipient: recipientId
            });
        } else {
            socket.emit('typing', {
                is_typing: false,
                room: roomName
            });
        }
    }
    
    // إضافة رسالة إلى الواجهة
    function addMessage(data, isStatus) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        
        if (isStatus) {
            messageElement.classList.add('message-status');
            messageElement.innerHTML = `
                <div class="text-center text-muted">${data.msg}</div>
            `;
        } else {
            const isOutgoing = data.user_id === currentUserId;
            messageElement.classList.add(isOutgoing ? 'message-outgoing' : 'message-incoming');
            
            const messageTime = new Date(data.timestamp).toLocaleTimeString();
            
            messageElement.innerHTML = `
                <div class="message-header">
                    <span class="message-sender">${data.username}</span>
                    <span class="message-time">${messageTime}</span>
                </div>
                <div class="message-content">${data.message}</div>
            `;
        }
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // التمرير التلقائي للأسفل
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // تحديث نشاط المستخدم
    setInterval(() => {
        socket.emit('user_activity');
    }, 30000);
});
// static/js/chat.js
document.getElementById('message-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    try {
        // إرسال الرسالة إلى الخادم
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room_id: currentRoomId,
                content: message,
                message_type: 'text'
            })
        });
        
        if (response.ok) {
            messageInput.value = '';
            // الرسالة ستضاف تلقائياً via Socket.io
        } else {
            throw new Error('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showNotification('فشل إرسال الرسالة', 'error');
    }
});