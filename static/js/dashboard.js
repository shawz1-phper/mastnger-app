// dashboard.js - إدارة الغرف والواجهة
document.addEventListener('DOMContentLoaded', function() {
    const roomsList = document.getElementById('rooms-list');
    const chatContainer = document.getElementById('chat-container');
    const welcomeMessage = document.getElementById('welcome-message');
    let currentRoomId = null;
    let supabaseSubscription = null;

    // تهيئة Supabase
    const supabase = supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);

    // تحميل الغرف عند البدء
    loadUserRooms();
    loadOnlineUsers();
    setupEventListeners();
    // تحديث حالة المستخدمين المتصلين
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
    
    // Socket.io للتحديثات الفورية
    socket.on('user_online', (userData) => {
        addOnlineUser(userData);
    });
    
    socket.on('user_offline', (userId) => {
        removeOnlineUser(userId);
    });
    
    
    // تحديث قائمة المتصلين كل 30 ثانية
    setInterval(loadOnlineUsers, 30000);

    function setupEventListeners() {
        // إنشاء غرفة جديدة
        document.getElementById('create-room-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            await createNewRoom();
        });

        // البحث في الغرف
        document.getElementById('room-search').addEventListener('input', function(e) {
            filterRooms(e.target.value);
        });
    }

    async function loadUserRooms() {
        try {
            const response = await fetch('/api/rooms');
            const rooms = await response.json();
            
            displayRooms(rooms);
            subscribeToRoomsUpdates(rooms);
        } catch (error) {
            console.error('Error loading rooms:', error);
        }
    }

    function displayRooms(rooms) {
        roomsList.innerHTML = '';
        
        rooms.forEach(room => {
            const roomElement = document.createElement('a');
            roomElement.href = '#';
            roomElement.className = 'list-group-item list-group-item-action room-item';
            roomElement.dataset.roomId = room.id;
            roomElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${room.name}</h6>
                        <small class="text-muted">${room.description || 'لا يوجد وصف'}</small>
                    </div>
                    <span class="badge bg-primary rounded-pill" id="unread-${room.id}">
                        ${room.unread_count || 0}
                    </span>
                </div>
            `;
            
            roomElement.addEventListener('click', () => joinRoom(room.id));
            roomsList.appendChild(roomElement);
        });
    }

    async function joinRoom(roomId) {
        try {
            // إلغاء الاشتراك السابق إذا كان موجوداً
            if (supabaseSubscription) {
                supabaseSubscription.unsubscribe();
            }

            currentRoomId = roomId;
            
            // إخفاء رسالة الترحيب وإظهار الدردشة
            welcomeMessage.classList.add('d-none');
            chatContainer.classList.remove('d-none');
            
            // تحميل الرسائل
            await loadRoomMessages(roomId);
            
            // الاشتراك في التحديثات
            subscribeToRoomRealtime(roomId);
            
            // إعلام السيرفر بالانضمام
            socket.emit('join_room', { room_id: roomId });
            
            // تحديث واجهة الغرفة النشطة
            updateActiveRoomUI(roomId);
            
        } catch (error) {
            console.error('Error joining room:', error);
        }
    }

    async function loadRoomMessages(roomId) {
        try {
            const response = await fetch(`/api/messages/${roomId}`);
            const messages = await response.json();
            
            displayMessages(messages);
            resetUnreadCount(roomId);
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    function displayMessages(messages) {
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';
        
        messages.reverse().forEach(message => {
            addMessageToUI(message);
        });
        
        scrollToBottom();
    }

    function subscribeToRoomRealtime(roomId) {
        // الاشتراك في تحديثات Supabase Realtime
        supabaseSubscription = supabase
            .channel(`room-${roomId}`)
            .on('postgres_changes', {
                event: 'INSERT',
                schema: 'public',
                table: 'messages',
                filter: `room_id=eq.${roomId}`
            }, (payload) => {
                // إذا كانت الغرفة نشطة، عرض الرسالة
                if (currentRoomId === roomId) {
                    addMessageToUI(payload.new);
                    scrollToBottom();
                } else {
                    // زيادة عداد الرسائل غير المقروءة
                    incrementUnreadCount(roomId);
                }
            })
            .subscribe();
    }

    async function createNewRoom() {
        const formData = new FormData(document.getElementById('create-room-form'));
        const roomData = {
            name: formData.get('name'),
            description: formData.get('description'),
            is_public: formData.get('is_public') === 'on'
        };

        try {
            const response = await fetch('/api/rooms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(roomData)
            });

            if (response.ok) {
                const newRoom = await response.json();
                $('#createRoomModal').modal('hide');
                document.getElementById('create-room-form').reset();
                
                // الانضمام للغرفة الجديدة
                await joinRoom(newRoom.id);
                
                // إعادة تحميل قائمة الغرف
                await loadUserRooms();
            }
        } catch (error) {
            console.error('Error creating room:', error);
        }
    }

    async function loadOnlineUsers() {
        try {
            const response = await fetch('/api/users/online');
            const onlineUsers = await response.json();
            
            const onlineUsersContainer = document.getElementById('online-users');
            onlineUsersContainer.innerHTML = '';
            
            onlineUsers.forEach(user => {
                const userElement = document.createElement('div');
                userElement.className = 'list-group-item';
                userElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="online-indicator"></div>
                        <img src="/static/img/avatars/${user.avatar_url}" 
                             class="user-avatar-sm me-2" alt="${user.username}">
                        <span>${user.username}</span>
                    </div>
                `;
                onlineUsersContainer.appendChild(userElement);
            });
        } catch (error) {
            console.error('Error loading online users:', error);
        }
    }

    function updateActiveRoomUI(roomId) {
        // إزالة النشط من جميع الغرف
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // إضافة النشط للغرفة الحالية
        const currentRoom = document.querySelector(`.room-item[data-room-id="${roomId}"]`);
        if (currentRoom) {
            currentRoom.classList.add('active');
        }
    }

    function incrementUnreadCount(roomId) {
        const badge = document.getElementById(`unread-${roomId}`);
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.classList.add('bg-danger');
        }
    }

    function resetUnreadCount(roomId) {
        const badge = document.getElementById(`unread-${roomId}`);
        if (badge) {
            badge.textContent = '0';
            badge.classList.remove('bg-danger');
            badge.classList.add('bg-primary');
        }
    }

    function filterRooms(searchTerm) {
        const rooms = document.querySelectorAll('.room-item');
        rooms.forEach(room => {
            const roomName = room.querySelector('h6').textContent.toLowerCase();
            if (roomName.includes(searchTerm.toLowerCase())) {
                room.style.display = 'block';
            } else {
                room.style.display = 'none';
            }
        });
    }

    // التعامل مع مغادرة الصفحة
    window.addEventListener('beforeunload', () => {
        if (currentRoomId) {
            socket.emit('leave_room', { room_id: currentRoomId });
        }
        if (supabaseSubscription) {
            supabaseSubscription.unsubscribe();
        }
    });
});