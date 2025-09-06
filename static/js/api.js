// service عام للاتصال بالـ API
class APIService {
    constructor() {
        this.baseURL = '/api';
        this.token = localStorage.getItem('auth_token');
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': this.token ? `Bearer ${this.token}` : ''
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // token منتهي الصلاحية
                this.handleUnauthorized();
                throw new Error('Unauthorized');
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Request failed');
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    handleUnauthorized() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_id');
        window.location.href = '/login';
    }
    
    // methods مختصرة
    get(endpoint) {
        return this.request(endpoint);
    }
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
}

// إنشاء instance global
window.api = new APIService();