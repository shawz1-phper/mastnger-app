// search.js - إدارة وظائف البحث

document.addEventListener('DOMContentLoaded', function() {
    // تهيئة البحث إذا كانت الصفحة تحتوي على نموذج بحث
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        initSearchForm(searchForm);
    }
    
    // تهيئة البحث في الوقت الحقيقي إذا كان هناك حقل بحث
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        initLiveSearch(searchInput);
    }
    
    // تهيئة عوامل تصفية البحث إذا كانت موجودة
    const searchFilters = document.querySelectorAll('.search-filter');
    if (searchFilters.length > 0) {
        initSearchFilters(searchFilters);
    }
});
// static/js/search.js
let searchTimeout;

document.getElementById('search-input').addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    
    if (query.length > 2) {
        searchTimeout = setTimeout(() => {
            searchUsers(query);
        }, 500);
    } else {
        clearSearchResults();
    }
});

async function searchUsers(query) {
    try {
        const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
        const searchResults = await response.json();
        
        displaySearchResults(searchResults);
    } catch (error) {
        console.error('Search error:', error);
        showNotification('حدث خطأ أثناء البحث', 'error');
    }
}

function displaySearchResults(users) {
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '';
    
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'search-result';
        userElement.innerHTML = `
            <img src="/static/img/avatars/${user.avatar_url}" 
                 alt="${user.username}" class="user-avatar">
            <div>
                <strong>${user.username}</strong>
                <small>${user.is_online ? 'متصل الآن' : 'غير متصل'}</small>
            </div>
            <button onclick="startChatWith(${user.id})">محادثة</button>
        `;
        resultsContainer.appendChild(userElement);
    });
}
// تهيئة نموذج البحث
function initSearchForm(form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const searchQuery = this.querySelector('input[name="q"]').value.trim();
        if (searchQuery) {
            performSearch(searchQuery);
        }
    });
}

// تهيئة البحث في الوقت الحقيقي
function initLiveSearch(input) {
    let searchTimeout;
    
    input.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        
        const query = this.value.trim();
        if (query.length > 2) {
            searchTimeout = setTimeout(() => {
                performLiveSearch(query);
            }, 500);
        } else {
            clearSearchResults();
        }
    });
    
    // إضافة زر مسح البحث
    const clearButton = document.createElement('button');
    clearButton.type = 'button';
    clearButton.className = 'search-clear';
    clearButton.innerHTML = '<i class="fas fa-times"></i>';
    clearButton.style.display = 'none';
    
    clearButton.addEventListener('click', function() {
        input.value = '';
        input.focus();
        clearSearchResults();
        this.style.display = 'none';
    });
    
    input.parentNode.appendChild(clearButton);
    
    input.addEventListener('input', function() {
        clearButton.style.display = this.value ? 'block' : 'none';
    });
}

// تهيئة عوامل تصفية البحث
function initSearchFilters(filters) {
    filters.forEach(filter => {
        filter.addEventListener('change', function() {
            performFilteredSearch();
        });
    });
}

// تنفيذ البحث
function performSearch(query, filters = {}) {
    showLoading();
    
    // إضافة معلمات التصفية إذا كانت موجودة
    const params = new URLSearchParams();
    params.append('q', query);
    
    Object.keys(filters).forEach(key => {
        if (filters[key]) {
            params.append(key, filters[key]);
        }
    });
    
    fetch(`/search?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data, query);
            hideLoading();
        })
        .catch(error => {
            console.error('Search error:', error);
            showNotification('حدث خطأ أثناء البحث', 'error');
            hideLoading();
        });
}

// تنفيذ البحث في الوقت الحقيقي
function performLiveSearch(query) {
    fetch(`/search/live?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displayLiveSearchResults(data, query);
        })
        .catch(error => {
            console.error('Live search error:', error);
        });
}

// تنفيذ البحث مع التصفية
function performFilteredSearch() {
    const query = document.getElementById('search-input').value.trim();
    const filters = getSearchFilters();
    
    if (query) {
        performSearch(query, filters);
    }
}

// الحصول على عوامل التصفية المحددة
function getSearchFilters() {
    const filters = {};
    
    document.querySelectorAll('.search-filter').forEach(filter => {
        if (filter.checked || (filter.value && filter.tagName === 'SELECT')) {
            filters[filter.name] = filter.value;
        }
    });
    
    return filters;
}

// عرض نتائج البحث
function displaySearchResults(results, query) {
    const resultsContainer = document.getElementById('search-results');
    if (!resultsContainer) return;
    
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h4 class="text-muted">لم يتم العثور على نتائج</h4>
                <p class="text-muted">لم نعثر على أي نتائج تطابق "${query}"</p>
            </div>
        `;
        return;
    }
    
    let html = `<div class="search-info mb-4">
        <h5>نتائج البحث عن "${query}"</h5>
        <p>عثرنا على ${results.length} نتيجة</p>
    </div>`;
    
    results.forEach(result => {
        html += renderSearchResult(result);
    });
    
    resultsContainer.innerHTML = html;
    
    // إضافة مستمعي الأحداث للنتائج
    initResultEvents();
}

// عرض نتائج البحث في الوقت الحقيقي
function displayLiveSearchResults(results, query) {
    const liveResultsContainer = document.getElementById('live-search-results') || createLiveResultsContainer();
    
    if (results.length === 0) {
        liveResultsContainer.innerHTML = `
            <div class="p-3 text-center text-muted">
                لا توجد نتائج تطابق "${query}"
            </div>
        `;
        return;
    }
    
    let html = '';
    results.forEach(result => {
        html += renderLiveSearchResult(result);
    });
    
    liveResultsContainer.innerHTML = html;
    liveResultsContainer.style.display = 'block';
    
    // إضافة مستمعي الأحداث للنتائج المباشرة
    initLiveResultEvents();
}

// إنشاء حاوية لنتائج البحث المباشر إذا لم تكن موجودة
function createLiveResultsContainer() {
    const container = document.createElement('div');
    container.id = 'live-search-results';
    container.className = 'live-search-results';
    
    const searchInput = document.getElementById('search-input');
    searchInput.parentNode.appendChild(container);
    
    // إخفاء النتائج عند النقر خارجها
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !container.contains(e.target)) {
            container.style.display = 'none';
        }
    });
    
    return container;
}

// مسح نتائج البحث
function clearSearchResults() {
    const resultsContainer = document.getElementById('search-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }
    
    const liveResultsContainer = document.getElementById('live-search-results');
    if (liveResultsContainer) {
        liveResultsContainer.style.display = 'none';
    }
}

// عرض نتيجة بحث واحدة
function renderSearchResult(result) {
    switch (result.type) {
        case 'user':
            return `
                <div class="search-result card card-hover mb-3" data-type="user" data-id="${result.id}">
                    <div class="card-body d-flex align-items-center">
                        <img src="/static/img/avatars/${result.avatar}" class="user-avatar me-3" alt="${result.name}">
                        <div class="flex-grow-1">
                            <h5 class="card-title mb-1">${result.name}</h5>
                            <p class="card-text text-muted mb-0">مستخدم</p>
                        </div>
                        <button class="btn btn-primary btn-sm">عرض الملف</button>
                    </div>
                </div>
            `;
        
        case 'room':
            return `
                <div class="search-result card card-hover mb-3" data-type="room" data-id="${result.id}">
                    <div class="card-body">
                        <h5 class="card-title">${result.name}</h5>
                        <p class="card-text">${result.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">غرفة دردشة</small>
                            <button class="btn btn-primary btn-sm">انضم إلى الغرفة</button>
                        </div>
                    </div>
                </div>
            `;
        
        case 'message':
            return `
                <div class="search-result card card-hover mb-3" data-type="message" data-room="${result.room}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-subtitle mb-0">${result.username}</h6>
                            <small class="text-muted">${formatDate(result.timestamp)}</small>
                        </div>
                        <p class="card-text">${result.message}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">في غرفة: ${result.room}</small>
                            <button class="btn btn-outline-primary btn-sm">عرض المحادثة</button>
                        </div>
                    </div>
                </div>
            `;
        
        default:
            return '';
    }
}

// عرض نتيجة بحث مباشرة واحدة
function renderLiveSearchResult(result) {
    switch (result.type) {
        case 'user':
            return `
                <div class="live-search-result" data-type="user" data-id="${result.id}">
                    <div class="d-flex align-items-center p-2">
                        <img src="/static/img/avatars/${result.avatar}" class="user-avatar-sm me-2" alt="${result.name}">
                        <div class="flex-grow-1">
                            <div class="fw-medium">${result.name}</div>
                            <small class="text-muted">مستخدم</small>
                        </div>
                    </div>
                </div>
            `;
        
        case 'room':
            return `
                <div class="live-search-result" data-type="room" data-id="${result.id}">
                    <div class="p-2">
                        <div class="fw-medium">${result.name}</div>
                        <small class="text-muted">غرفة دردشة</small>
                    </div>
                </div>
            `;
        
        default:
            return '';
    }
}

// تهيئة أحداث النتائج
function initResultEvents() {
    document.querySelectorAll('.search-result').forEach(result => {
        result.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            const id = this.getAttribute('data-id');
            
            handleResultClick(type, id);
        });
    });
}

// تهيئة أحداث النتائج المباشرة
function initLiveResultEvents() {
    document.querySelectorAll('.live-search-result').forEach(result => {
        result.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            const id = this.getAttribute('data-id');
            
            handleResultClick(type, id);
            
            // إخفاء نتائج البحث المباشر
            const liveResultsContainer = document.getElementById('live-search-results');
            if (liveResultsContainer) {
                liveResultsContainer.style.display = 'none';
            }
            
            // مسح حقل البحث
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = '';
            }
        });
    });
}

// التعامل مع النقر على نتيجة
function handleResultClick(type, id) {
    switch (type) {
        case 'user':
            window.location.href = `/private/${id}`;
            break;
        
        case 'room':
            window.location.href = `/chat/${id}`;
            break;
        
        case 'message':
            const room = document.querySelector(`[data-type="message"][data-room="${id}"]`).getAttribute('data-room');
            window.location.href = `/chat/${room}`;
            break;
    }
}

// تنسيق التاريخ للعرض
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        return 'اليوم ' + date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
        return 'أمس ' + date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    } else if (days < 7) {
        return `منذ ${days} أيام`;
    } else {
        return date.toLocaleDateString('ar-EG');
    }
}

// حفظ بحث حديث
function saveRecentSearch(query, type) {
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
    
    // إزالة البحث إذا كان موجوداً مسبقاً
    recentSearches = recentSearches.filter(search => search.query !== query);
    
    // إضافة البحث إلى بداية القائمة
    recentSearches.unshift({
        query: query,
        type: type,
        timestamp: new Date().toISOString()
    });
    
    // الاحتفاظ بعدد محدد من عمليات البحث
    if (recentSearches.length > 5) {
        recentSearches = recentSearches.slice(0, 5);
    }
    
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
}

// تحميل عمليات البحث الحديثة
function loadRecentSearches() {
    const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
    const container = document.getElementById('recent-searches');
    
    if (!container || recentSearches.length === 0) return;
    
    let html = '<h6 class="mb-3">عمليات البحث الحديثة</h6>';
    
    recentSearches.forEach(search => {
        html += `
            <div class="recent-search-item p-2 mb-2 rounded" data-query="${search.query}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="fas fa-search me-2 text-muted"></i>
                        <span>${search.query}</span>
                    </div>
                    <button class="btn btn-sm btn-link text-muted remove-search">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // إضافة مستمعي الأحداث
    container.querySelectorAll('.recent-search-item').forEach(item => {
        item.addEventListener('click', function(e) {
            if (!e.target.closest('.remove-search')) {
                const query = this.getAttribute('data-query');
                document.getElementById('search-input').value = query;
                performSearch(query);
            }
        });
        
        const removeBtn = item.querySelector('.remove-search');
        if (removeBtn) {
            removeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const query = item.getAttribute('data-query');
                removeRecentSearch(query);
                item.remove();
            });
        }
    });
}

// إزالة بحث حديث
function removeRecentSearch(query) {
    let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
    recentSearches = recentSearches.filter(search => search.query !== query);
    localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
}