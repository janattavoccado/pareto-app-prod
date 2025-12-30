/**
 * Pareto Admin Dashboard - JavaScript (Final Version)
 * Complete implementation with authentication, dashboard, tenants, and users CRUD
 */

const API_BASE_URL = window.location.origin + '/api';
let sessionToken = localStorage.getItem('sessionToken');
let currentAdminInfo = null;
let currentEditingId = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔧 Dashboard initializing...');
    setupEventListeners();
    if (sessionToken) {
        console.log('🔍 Validating existing session...');
        await validateSession();
    } else {
        console.log('❌ No session token, showing login');
        showLoginModal();
    }
});

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    const loginForm = document.getElementById('loginForm');
    const logoutBtn = document.getElementById('logoutBtn');
    const addTenantBtn = document.getElementById('addTenantBtn');
    const tenantForm = document.getElementById('tenantForm');
    const addUserBtn = document.getElementById('addUserBtn');
    const userForm = document.getElementById('userForm');
    
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
    if (addTenantBtn) addTenantBtn.addEventListener('click', () => openTenantModal(null));
    if (tenantForm) tenantForm.addEventListener('submit', handleSaveTenant);
    if (addUserBtn) addUserBtn.addEventListener('click', () => openUserModal(null));
    if (userForm) userForm.addEventListener('submit', handleSaveUser);
    
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', () => navigateToPage(item.dataset.page));
    });
}

// ============================================================================
// Authentication
// ============================================================================

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        if (data.success && data.session_token) {
            sessionToken = data.session_token;
            localStorage.setItem('sessionToken', sessionToken);
            currentAdminInfo = data.admin;
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
            showAlert('Login successful!', 'success');
        } else {
            showAlert(data.message || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('An error occurred during login', 'error');
    }
}

async function validateSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/validate`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        if (data.success && data.admin) {
            currentAdminInfo = data.admin;
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
        } else {
            logout(true);
        }
    } catch (error) {
        console.error('Session validation error:', error);
        logout(true);
    }
}

async function logout(soft = false) {
    if (sessionToken) {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${sessionToken}` }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
    sessionToken = null;
    localStorage.removeItem('sessionToken');
    currentAdminInfo = null;
    showLoginModal();
    if (!soft) showAlert('You have been logged out', 'info');
}

// ============================================================================
// UI Management
// ============================================================================

function showLoginModal() {
    const modal = document.getElementById('loginModal');
    const container = document.querySelector('.container-main');
    if (modal) modal.classList.add('active');
    if (container) container.style.display = 'none';
}

function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    const container = document.querySelector('.container-main');
    if (modal) modal.classList.remove('active');
    if (container) container.style.display = 'flex';
}

function updateAdminInfo() {
    if (currentAdminInfo) {
        const nameEl = document.getElementById('adminName');
        const avatarEl = document.getElementById('userAvatar');
        if (nameEl) nameEl.textContent = currentAdminInfo.username || 'Admin';
        if (avatarEl) {
            let initials = 'AD';
            if (currentAdminInfo.full_name && typeof currentAdminInfo.full_name === 'string') {
                initials = currentAdminInfo.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
            } else if (currentAdminInfo.username) {
                initials = currentAdminInfo.username.substring(0, 2).toUpperCase();
            }
            avatarEl.textContent = initials;
        }
    }
}

function navigateToPage(page) {
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`[data-page="${page}"]`);
    if (activeItem) activeItem.classList.add('active');
    
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    const pageEl = document.getElementById(`${page}Page`);
    if (pageEl) pageEl.classList.remove('hidden');
    
    if (page === 'dashboard') loadDashboard();
    else if (page === 'tenants') loadTenants();
    else if (page === 'users') loadUsers();
}

// ============================================================================
// Dashboard
// ============================================================================

async function loadDashboard() {
    try {
        const result = await apiRequest('/admin/dashboard');
        if (result.success && result.data) {
            const stats = result.data.statistics || {};
            const totalTenantsEl = document.getElementById('totalTenants');
            const totalUsersEl = document.getElementById('totalUsers');
            const totalAdminsEl = document.getElementById('totalAdmins');
            
            if (totalTenantsEl) totalTenantsEl.textContent = stats.tenant_count ?? '0';
            if (totalUsersEl) totalUsersEl.textContent = stats.user_count ?? '0';
            if (totalAdminsEl) totalAdminsEl.textContent = stats.admin_count ?? '0';
        }
    } catch (error) {
        showAlert('Failed to load dashboard', 'error');
    }
}

// ============================================================================
// Tenants Page
// ============================================================================

async function loadTenants() {
    try {
        const result = await apiRequest('/admin/tenants');
        if (result.success) {
            renderTenantsTable(result.data);
        }
    } catch (error) {
        showAlert('Failed to load tenants', 'error');
    }
}

function renderTenantsTable(tenants) {
    const tbody = document.getElementById('tenantsTable')?.querySelector('tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    if (!tenants || tenants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">No tenants found</td></tr>';
        return;
    }
    
    tenants.forEach(tenant => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${tenant.name}</td>
            <td>${tenant.is_active ? '✓ Active' : '✗ Inactive'}</td>
            <td>
                <button class="btn-sm" onclick="openTenantModal(${JSON.stringify(tenant).replace(/"/g, '&quot;')})">Edit</button>
                <button class="btn-sm btn-danger" onclick="deleteTenant(${tenant.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function openTenantModal(tenant) {
    currentEditingId = tenant ? tenant.id : null;
    const titleEl = document.getElementById('tenantModalTitle');
    const nameEl = document.getElementById('tenantName');
    const activeEl = document.getElementById('tenantIsActive');
    
    if (titleEl) titleEl.textContent = tenant ? 'Edit Tenant' : 'Add New Tenant';
    if (nameEl) nameEl.value = tenant ? tenant.name : '';
    if (activeEl) activeEl.checked = tenant ? tenant.is_active : true;
    
    const modal = document.getElementById('tenantModal');
    if (modal) modal.classList.add('active');
}

async function handleSaveTenant(e) {
    e.preventDefault();
    const nameEl = document.getElementById('tenantName');
    const activeEl = document.getElementById('tenantIsActive');
    
    const data = {
        name: nameEl?.value || '',
        is_active: activeEl?.checked || true
    };
    
    const endpoint = currentEditingId ? `/admin/tenants/${currentEditingId}` : '/admin/tenants';
    const method = currentEditingId ? 'PUT' : 'POST';
    
    try {
        const result = await apiRequest(endpoint, { method, body: JSON.stringify(data) });
        if (result.success) {
            showAlert(`Tenant ${currentEditingId ? 'updated' : 'created'} successfully!`, 'success');
            const modal = document.getElementById('tenantModal');
            if (modal) modal.classList.remove('active');
            loadTenants();
        }
    } catch (error) {
        // Error already shown
    }
}

async function deleteTenant(id) {
    if (confirm('Delete this tenant?')) {
        try {
            const result = await apiRequest(`/admin/tenants/${id}`, { method: 'DELETE' });
            if (result.success) {
                showAlert('Tenant deleted!', 'success');
                loadTenants();
            }
        } catch (error) {
            // Error already shown
        }
    }
}

// ============================================================================
// Users Page
// ============================================================================

async function loadUsers() {
    try {
        const result = await apiRequest('/admin/users');
        if (result.success) {
            renderUsersTable(result.data);
        }
    } catch (error) {
        showAlert('Failed to load users', 'error');
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('usersTable')?.querySelector('tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No users found</td></tr>';
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.phone_number}</td>
            <td>${user.email || 'N/A'}</td>
            <td>${user.first_name || ''} ${user.last_name || ''}</td>
            <td>${user.is_enabled ? '✓ Enabled' : '✗ Disabled'}</td>
            <td>
                <button class="btn-sm" onclick="openUserModal(${JSON.stringify(user).replace(/"/g, '&quot;')})">Edit</button>
                <button class="btn-sm btn-danger" onclick="deleteUser(${user.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function openUserModal(user) {
    currentEditingId = user ? user.id : null;
    const titleEl = document.getElementById('userModalTitle');
    const phoneEl = document.getElementById('userPhoneNumber');
    const emailEl = document.getElementById('userEmail');
    const firstEl = document.getElementById('userFirstName');
    const lastEl = document.getElementById('userLastName');
    const enabledEl = document.getElementById('userIsEnabled');
    
    if (titleEl) titleEl.textContent = user ? 'Edit User' : 'Add New User';
    if (phoneEl) phoneEl.value = user ? user.phone_number : '';
    if (emailEl) emailEl.value = user ? user.email : '';
    if (firstEl) firstEl.value = user ? user.first_name : '';
    if (lastEl) lastEl.value = user ? user.last_name : '';
    if (enabledEl) enabledEl.checked = user ? user.is_enabled : true;
    
    const modal = document.getElementById('userModal');
    if (modal) modal.classList.add('active');
}

async function handleSaveUser(e) {
    e.preventDefault();
    const phoneEl = document.getElementById('userPhoneNumber');
    const emailEl = document.getElementById('userEmail');
    const firstEl = document.getElementById('userFirstName');
    const lastEl = document.getElementById('userLastName');
    const enabledEl = document.getElementById('userIsEnabled');
    
    const data = {
        phone_number: phoneEl?.value || '',
        email: emailEl?.value || '',
        first_name: firstEl?.value || '',
        last_name: lastEl?.value || '',
        is_enabled: enabledEl?.checked || true
    };
    
    const endpoint = currentEditingId ? `/admin/users/${currentEditingId}` : '/admin/users';
    const method = currentEditingId ? 'PUT' : 'POST';
    
    try {
        const result = await apiRequest(endpoint, { method, body: JSON.stringify(data) });
        if (result.success) {
            showAlert(`User ${currentEditingId ? 'updated' : 'created'} successfully!`, 'success');
            const modal = document.getElementById('userModal');
            if (modal) modal.classList.remove('active');
            loadUsers();
        }
    } catch (error) {
        // Error already shown
    }
}

async function deleteUser(id) {
    if (confirm('Delete this user?')) {
        try {
            const result = await apiRequest(`/admin/users/${id}`, { method: 'DELETE' });
            if (result.success) {
                showAlert('User deleted!', 'success');
                loadUsers();
            }
        } catch (error) {
            // Error already shown
        }
    }
}

// ============================================================================
// Utilities
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    const config = {
        headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        const data = await response.json();
        if (!response.ok) {
            showAlert(data.message || `Error: ${response.status}`, 'error');
            throw new Error(data.message || `HTTP ${response.status}`);
        }
        return data;
    } catch (error) {
        console.error(`API error: ${endpoint}`, error);
        throw error;
    }
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    if (!container) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alert.style.padding = '12px 16px';
    alert.style.marginBottom = '8px';
    alert.style.borderRadius = '4px';
    alert.style.backgroundColor = type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1';
    alert.style.color = type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460';
    
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

console.log('✅ Dashboard script loaded');
