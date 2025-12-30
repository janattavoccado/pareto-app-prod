/**
 * Pareto Admin Dashboard - JavaScript (v2 - Fixed Session Handling)
 * Handles all dashboard functionality, API calls, and UI interactions
 */

const API_BASE_URL = window.location.origin + '/api';
let sessionToken = localStorage.getItem('sessionToken');
let currentAdminInfo = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Dashboard initializing...');
    console.log('📝 Session token:', sessionToken ? 'EXISTS' : 'MISSING');
    
    // Setup event listeners first
    setupEventListeners();
    
    // Check for existing session token
    if (sessionToken) {
        console.log('🔍 Validating existing session...');
        await validateSession();
    } else {
        console.log('❌ No session token found, showing login modal');
        showLoginModal();
    }
});

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    const themeToggle = document.getElementById('themeToggle');
    const logoutBtn = document.getElementById('logoutBtn');
    const loginForm = document.getElementById('loginForm');
    
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    
    // Sidebar navigation
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', () => navigateToPage(item.dataset.page));
    });
}

// ============================================================================
// Theme Management
// ============================================================================

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.className = savedTheme + '-mode';
}

function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('light-mode', !isDark);
    const newTheme = isDark ? 'dark' : 'light';
    localStorage.setItem('theme', newTheme);
}

// ============================================================================
// Authentication
// ============================================================================

async function handleLogin(e) {
    e.preventDefault();
    console.log('🔐 Handling login...');
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginError = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        console.log('📨 Login response:', data.success ? 'SUCCESS' : 'FAILED');
        
        if (data.success && data.session_token) {
            sessionToken = data.session_token;
            localStorage.setItem('sessionToken', sessionToken);
            currentAdminInfo = data.admin;
            
            console.log('✅ Login successful, hiding modal');
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
            showAlert('Login successful!', 'success');
        } else {
            console.log('❌ Login failed:', data.message);
            if (loginError) {
                loginError.classList.remove('hidden');
                document.getElementById('loginErrorMsg').textContent = data.message || 'Login failed';
            }
        }
    } catch (error) {
        console.error('❌ Login error:', error);
        if (loginError) {
            loginError.classList.remove('hidden');
            document.getElementById('loginErrorMsg').textContent = 'An error occurred during login';
        }
    }
}

async function validateSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/validate`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        console.log('📨 Session validation response:', data.success ? 'VALID' : 'INVALID');
        
        if (data.success && data.admin) {
            currentAdminInfo = data.admin;
            console.log('✅ Session valid, hiding modal');
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
        } else {
            console.log('❌ Session invalid, showing login');
            logout(true);
        }
    } catch (error) {
        console.error('❌ Session validation error:', error);
        logout(true);
    }
}

async function logout(soft = false) {
    console.log('🚪 Logging out...');
    
    if (sessionToken) {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${sessionToken}` }
            });
        } catch (error) {
            console.error('⚠️  Logout API call failed:', error);
        }
    }
    
    sessionToken = null;
    localStorage.removeItem('sessionToken');
    currentAdminInfo = null;
    showLoginModal();
    
    if (!soft) {
        showAlert('You have been logged out.', 'info');
    }
}

// ============================================================================
// UI Management
// ============================================================================

function showLoginModal() {
    console.log('🎯 Showing login modal');
    const loginModal = document.getElementById('loginModal');
    const containerMain = document.querySelector('.container-main');
    
    if (loginModal) loginModal.classList.add('active');
    if (containerMain) containerMain.style.display = 'none';
}

function hideLoginModal() {
    console.log('🎯 Hiding login modal');
    const loginModal = document.getElementById('loginModal');
    const containerMain = document.querySelector('.container-main');
    
    if (loginModal) loginModal.classList.remove('active');
    if (containerMain) containerMain.style.display = 'flex';
}

function updateAdminInfo() {
    if (currentAdminInfo) {
        const adminNameEl = document.getElementById('adminName');
        const userAvatarEl = document.getElementById('userAvatar');
        
        if (adminNameEl) {
            adminNameEl.textContent = currentAdminInfo.username || 'Admin';
        }
        
        if (userAvatarEl) {
            let initials = 'AD';
            if (currentAdminInfo.full_name && typeof currentAdminInfo.full_name === 'string') {
                initials = currentAdminInfo.full_name
                    .split(' ')
                    .map(n => n[0])
                    .join('')
                    .toUpperCase();
            } else if (currentAdminInfo.username) {
                initials = currentAdminInfo.username.substring(0, 2).toUpperCase();
            }
            userAvatarEl.textContent = initials;
        }
    }
}

// ============================================================================
// Navigation
// ============================================================================

function navigateToPage(page) {
    console.log('📄 Navigating to:', page);
    
    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`[data-page="${page}"]`);
    if (activeItem) activeItem.classList.add('active');
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    
    // Show selected page
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) {
        pageElement.classList.remove('hidden');
        
        // Load page data
        if (page === 'dashboard') {
            loadDashboard();
        } else if (page === 'tenants') {
            loadTenants();
        } else if (page === 'users') {
            loadUsers();
        }
    }
}

// ============================================================================
// Dashboard
// ============================================================================

async function loadDashboard() {
    console.log('📊 Loading dashboard...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/dashboard`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const result = await response.json();
        console.log('📨 Dashboard response:', result.success ? 'SUCCESS' : 'FAILED');
        
        if (result.success && result.data) {
            const stats = result.data.statistics || {};
            
            // Update statistics
            const totalTenantsEl = document.getElementById('totalTenants');
            const totalUsersEl = document.getElementById('totalUsers');
            const totalAdminsEl = document.getElementById('totalAdmins');
            
            if (totalTenantsEl) totalTenantsEl.textContent = stats.tenant_count ?? '0';
            if (totalUsersEl) totalUsersEl.textContent = stats.user_count ?? '0';
            if (totalAdminsEl) totalAdminsEl.textContent = stats.admin_count ?? '0';
            
            console.log('✅ Dashboard statistics updated');
            
            // Render recent data
            if (result.data.recent_tenants) {
                renderRecentTenants(result.data.recent_tenants);
            }
            if (result.data.recent_users) {
                renderRecentUsers(result.data.recent_users);
            }
        } else {
            console.log('⚠️  Dashboard response incomplete');
        }
    } catch (error) {
        console.error('❌ Dashboard load error:', error);
        showAlert('Failed to load dashboard data', 'error');
    }
}

function renderRecentTenants(tenants) {
    const container = document.getElementById('recentTenantsContainer');
    if (!container) return;
    
    if (!tenants || tenants.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">No recent tenants</p>';
        return;
    }
    
    let html = '<table style="width: 100%; border-collapse: collapse;"><thead><tr><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Name</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Status</th></tr></thead><tbody>';
    
    tenants.forEach(tenant => {
        const status = tenant.is_active ? '<span style="color: green;">✓ Active</span>' : '<span style="color: red;">✗ Inactive</span>';
        html += `<tr><td style="padding: 8px; border-bottom: 1px solid #eee;">${tenant.name}</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${status}</td></tr>`;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderRecentUsers(users) {
    const container = document.getElementById('recentUsersContainer');
    if (!container) return;
    
    if (!users || users.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">No recent users</p>';
        return;
    }
    
    let html = '<table style="width: 100%; border-collapse: collapse;"><thead><tr><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Phone</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Email</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Status</th></tr></thead><tbody>';
    
    users.forEach(user => {
        const status = user.is_enabled ? '<span style="color: green;">✓ Enabled</span>' : '<span style="color: red;">✗ Disabled</span>';
        html += `<tr><td style="padding: 8px; border-bottom: 1px solid #eee;">${user.phone_number}</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${user.email || 'N/A'}</td><td style="padding: 8px; border-bottom: 1px solid #eee;">${status}</td></tr>`;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// ============================================================================
// Utility Functions
// ============================================================================

function showAlert(message, type = 'info') {
    console.log(`🔔 Alert [${type}]:`, message);
    
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alert.style.padding = '12px 16px';
    alert.style.marginBottom = '8px';
    alert.style.borderRadius = '4px';
    alert.style.backgroundColor = type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1';
    alert.style.color = type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460';
    
    alertContainer.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

// ============================================================================
// Tenants Page
// ============================================================================

async function loadTenants() {
    console.log('📋 Loading tenants...');
    try {
        const response = await fetch(`${API_BASE_URL}/admin/tenants`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const result = await response.json();
        if (result.success) {
            renderTenantsTable(result.data);
        } else {
            showAlert('Failed to load tenants', 'error');
        }
    } catch (error) {
        console.error('❌ Error loading tenants:', error);
        showAlert('Failed to load tenants', 'error');
    }
}

function renderTenantsTable(tenants) {
    const tbody = document.querySelector('#tenantsTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    if (!tenants || tenants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 20px;">No tenants found</td></tr>';
        return;
    }
    
    tenants.forEach(tenant => {
        const row = document.createElement('tr');
        const status = tenant.is_active ? '✓ Active' : '✗ Inactive';
        row.innerHTML = `
            <td style="padding: 8px;">${tenant.name}</td>
            <td style="padding: 8px;">${status}</td>
            <td style="padding: 8px;"><button onclick="alert('Edit tenant ${tenant.id}')">Edit</button> <button onclick="alert('Delete tenant ${tenant.id}')">Delete</button></td>
        `;
        tbody.appendChild(row);
    });
}

// ============================================================================
// Users Page
// ============================================================================

async function loadUsers() {
    console.log('👥 Loading users...');
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const result = await response.json();
        if (result.success) {
            renderUsersTable(result.data);
        } else {
            showAlert('Failed to load users', 'error');
        }
    } catch (error) {
        console.error('❌ Error loading users:', error);
        showAlert('Failed to load users', 'error');
    }
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px;">No users found</td></tr>';
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        const status = user.is_enabled ? '✓ Enabled' : '✗ Disabled';
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'N/A';
        row.innerHTML = `
            <td style="padding: 8px;">${user.phone_number}</td>
            <td style="padding: 8px;">${user.email || 'N/A'}</td>
            <td style="padding: 8px;">${fullName}</td>
            <td style="padding: 8px;">${status}</td>
            <td style="padding: 8px;"><button onclick="alert('Edit user ${user.id}')">Edit</button> <button onclick="alert('Delete user ${user.id}')">Delete</button></td>
        `;
        tbody.appendChild(row);
    });
}

// Placeholder functions
async function loadAuditLogs() { console.log('📜 Loading audit logs...'); }
async function loadSettings() { console.log('⚙️  Loading settings...'); }

console.log('✅ Admin Dashboard script loaded');
