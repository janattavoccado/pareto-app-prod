/**
 * Pareto Admin Dashboard - JavaScript
 * Handles all dashboard functionality, API calls, and UI interactions
 */

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = window.location.origin + '/api';
let sessionToken = localStorage.getItem('sessionToken');
let currentAdminInfo = null;
let currentEditingUserId = null;
let currentDeleteTarget = null;
let tenants = [];

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Load theme preference
    loadTheme();
    
    // Check if logged in
    if (sessionToken) {
        await validateSession();
    } else {
        showLoginModal();
    }
    
    // Event listeners
    setupEventListeners();
});

// ============================================================================
// Theme Management
// ============================================================================

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        document.getElementById('themeToggle').textContent = 'brightness_7';
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.getElementById('themeToggle').textContent = isDark ? 'brightness_7' : 'brightness_4';
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);
    
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Sidebar navigation
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', () => navigateToPage(item.dataset.page));
    });
    
    // User management
    document.getElementById('addUserBtn').addEventListener('click', openAddUserModal);
    document.getElementById('userForm').addEventListener('submit', handleSaveUser);
    document.getElementById('userSearchInput').addEventListener('input', filterUsers);
    document.getElementById('userFilterEnabled').addEventListener('change', filterUsers);
    
    // Settings
    document.getElementById('changePasswordForm').addEventListener('submit', handleChangePassword);
    
    // Audit logs filters
    document.getElementById('auditFilterAction').addEventListener('change', loadAuditLogs);
    document.getElementById('auditFilterEntity').addEventListener('change', loadAuditLogs);
}

// ============================================================================
// Authentication
// ============================================================================

async function handleLogin(e) {
    e.preventDefault();
    
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
        
        if (data.success) {
            sessionToken = data.session_token;
            localStorage.setItem('sessionToken', sessionToken);
            currentAdminInfo = data.admin;
            
            // Hide login modal and load dashboard
            document.getElementById('loginModal').classList.remove('active');
            updateAdminInfo();
            await loadDashboard();
            
            showAlert('Login successful!', 'success');
        } else {
            loginError.classList.remove('hidden');
            document.getElementById('loginErrorMsg').textContent = data.message || 'Login failed';
        }
    } catch (error) {
        console.error('Login error:', error);
        loginError.classList.remove('hidden');
        document.getElementById('loginErrorMsg').textContent = 'An error occurred during login';
    }
}

async function validateSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/validate`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentAdminInfo = data.admin;
            updateAdminInfo();
            await loadDashboard();
        } else {
            sessionToken = null;
            localStorage.removeItem('sessionToken');
            showLoginModal();
        }
    } catch (error) {
        console.error('Session validation error:', error);
        sessionToken = null;
        localStorage.removeItem('sessionToken');
        showLoginModal();
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    sessionToken = null;
    localStorage.removeItem('sessionToken');
    currentAdminInfo = null;
    showLoginModal();
}

function showLoginModal() {
    document.getElementById('loginModal').classList.add('active');
    document.querySelector('.container-main').style.display = 'none';
}

function updateAdminInfo() {
    if (currentAdminInfo) {
        document.getElementById('adminName').textContent = currentAdminInfo.username;
        const initials = currentAdminInfo.full_name
            .split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase();
        document.getElementById('userAvatar').textContent = initials;
    }
}

// ============================================================================
// Navigation
// ============================================================================

function navigateToPage(page) {
    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => {
        p.classList.add('hidden');
    });
    
    // Show selected page
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) {
        pageElement.classList.remove('hidden');
        
        // Load page data
        if (page === 'dashboard') {
            loadDashboard();
        } else if (page === 'users') {
            loadUsers();
        } else if (page === 'tenants') {
            loadTenants();
        } else if (page === 'audit-logs') {
            loadAuditLogs();
        }
    }
}

// ============================================================================
// Dashboard
// ============================================================================

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/dashboard`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update stats
            document.getElementById('totalTenants').textContent = data.statistics.total_tenants;
            document.getElementById('totalUsers').textContent = data.statistics.total_users;
            document.getElementById('activeUsers').textContent = data.statistics.active_users;
            document.getElementById('totalAdmins').textContent = data.statistics.total_admins;
            
            // Update recent activity
            const activityContainer = document.getElementById('recentActivityContainer');
            if (data.recent_activity.length > 0) {
                let html = '<table style="width: 100%;"><thead><tr><th>Admin</th><th>Action</th><th>Entity</th><th>Date/Time</th></tr></thead><tbody>';
                data.recent_activity.forEach(log => {
                    const date = new Date(log.created_at).toLocaleString();
                    html += `<tr><td>${log.admin}</td><td>${log.action}</td><td>${log.entity_type}</td><td>${date}</td></tr>`;
                });
                html += '</tbody></table>';
                activityContainer.innerHTML = html;
            } else {
                activityContainer.innerHTML = '<p style="text-align: center; color: #7f8c8d;">No recent activity</p>';
            }
        }
    } catch (error) {
        console.error('Dashboard load error:', error);
        showAlert('Failed to load dashboard', 'error');
    }
}

// ============================================================================
// Users Management
// ============================================================================

async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayUsers(data.users);
        }
    } catch (error) {
        console.error('Users load error:', error);
        showAlert('Failed to load users', 'error');
    }
}

function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.full_name}</td>
            <td>${user.phone_number}</td>
            <td>${user.email || '-'}</td>
            <td>
                <span class="badge ${user.enabled ? 'badge-success' : 'badge-danger'}">
                    ${user.enabled ? 'Enabled' : 'Disabled'}
                </span>
            </td>
            <td>
                <button class="btn btn-primary btn-small" onclick="openEditUserModal(${user.id})">
                    <i class="material-icons" style="font-size: 16px;">edit</i>
                </button>
                <button class="btn btn-info btn-small" onclick="openTokenModal(${user.id}, '${user.full_name}')">
                    <i class="material-icons" style="font-size: 16px;">vpn_key</i>
                </button>
                <button class="btn btn-danger btn-small" onclick="openDeleteUserModal(${user.id}, '${user.full_name}')">
                    <i class="material-icons" style="font-size: 16px;">delete</i>
                </button>
            </td>
        </tr>
    `).join('');
}

function filterUsers() {
    const searchTerm = document.getElementById('userSearchInput').value.toLowerCase();
    const filterEnabled = document.getElementById('userFilterEnabled').value;
    
    const rows = document.querySelectorAll('#usersTableBody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const statusCell = row.querySelector('td:nth-child(4)');
        const status = statusCell.textContent.toLowerCase();
        
        const matchesSearch = text.includes(searchTerm);
        const matchesFilter = !filterEnabled || 
                            (filterEnabled === 'true' && status.includes('enabled')) ||
                            (filterEnabled === 'false' && status.includes('disabled'));
        
        row.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
    });
}

async function loadTenants() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/tenants`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            tenants = data.tenants;
            displayTenants(data.tenants);
            
            // Also populate tenant dropdown in user modal
            const tenantSelect = document.getElementById('userTenant');
            tenantSelect.innerHTML = data.tenants.map(t => 
                `<option value="${t.id}">${t.company_name}</option>`
            ).join('');
        }
    } catch (error) {
        console.error('Tenants load error:', error);
        showAlert('Failed to load tenants', 'error');
    }
}

function displayTenants(tenants) {
    const tbody = document.getElementById('tenantsTableBody');
    
    if (tenants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No tenants found</td></tr>';
        return;
    }
    
    tbody.innerHTML = tenants.map(tenant => `
        <tr>
            <td>${tenant.company_name}</td>
            <td>${tenant.email || '-'}</td>
            <td>${tenant.phone || '-'}</td>
            <td>${tenant.user_count}</td>
            <td>
                <span class="badge ${tenant.active ? 'badge-success' : 'badge-danger'}">
                    ${tenant.active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <button class="btn btn-primary btn-small" onclick="viewTenantUsers(${tenant.id})">
                    <i class="material-icons" style="font-size: 16px;">visibility</i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function viewTenantUsers(tenantId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/tenants/${tenantId}`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const users = data.users;
            let message = `<strong>${data.tenant.company_name}</strong><br><br>`;
            message += `<strong>Users (${users.length}):</strong><br>`;
            message += users.map(u => `${u.full_name} (${u.phone_number})`).join('<br>');
            
            showAlert(message, 'info');
        }
    } catch (error) {
        console.error('Error viewing tenant users:', error);
        showAlert('Failed to load tenant users', 'error');
    }
}

// ============================================================================
// User Modal Functions
// ============================================================================

function openAddUserModal() {
    currentEditingUserId = null;
    document.getElementById('userModalTitle').textContent = 'Add User';
    document.getElementById('userForm').reset();
    document.getElementById('userModal').classList.add('active');
    
    // Load tenants if not already loaded
    if (tenants.length === 0) {
        loadTenants();
    }
}

async function openEditUserModal(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const user = data.user;
            currentEditingUserId = userId;
            
            document.getElementById('userModalTitle').textContent = 'Edit User';
            document.getElementById('userTenant').value = user.tenant_id;
            document.getElementById('userFirstName').value = user.first_name;
            document.getElementById('userLastName').value = user.last_name;
            document.getElementById('userPhone').value = user.phone_number;
            document.getElementById('userEmail').value = user.email || '';
            document.getElementById('userEnabled').checked = user.enabled;
            
            document.getElementById('userModal').classList.add('active');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        showAlert('Failed to load user details', 'error');
    }
}

function closeUserModal() {
    document.getElementById('userModal').classList.remove('active');
    currentEditingUserId = null;
}

async function handleSaveUser(e) {
    e.preventDefault();
    
    const userData = {
        tenant_id: parseInt(document.getElementById('userTenant').value),
        first_name: document.getElementById('userFirstName').value,
        last_name: document.getElementById('userLastName').value,
        phone_number: document.getElementById('userPhone').value,
        email: document.getElementById('userEmail').value,
        enabled: document.getElementById('userEnabled').checked
    };
    
    try {
        let response;
        
        if (currentEditingUserId) {
            // Update existing user
            response = await fetch(`${API_BASE_URL}/admin/users/${currentEditingUserId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionToken}`
                },
                body: JSON.stringify(userData)
            });
        } else {
            // Create new user
            response = await fetch(`${API_BASE_URL}/admin/users`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionToken}`
                },
                body: JSON.stringify(userData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(data.message, 'success');
            closeUserModal();
            await loadUsers();
        } else {
            showAlert(data.message || 'Failed to save user', 'error');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        showAlert('An error occurred while saving user', 'error');
    }
}

function openDeleteUserModal(userId, userName) {
    currentDeleteTarget = { type: 'user', id: userId, name: userName };
    document.getElementById('deleteMessage').textContent = `Are you sure you want to delete user "${userName}"? This action cannot be undone.`;
    document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('active');
    currentDeleteTarget = null;
}

document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
    if (!currentDeleteTarget) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${currentDeleteTarget.id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('User deleted successfully', 'success');
            closeDeleteModal();
            await loadUsers();
        } else {
            showAlert(data.message || 'Failed to delete user', 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showAlert('An error occurred while deleting user', 'error');
    }
});

// ============================================================================
// Audit Logs
// ============================================================================

async function loadAuditLogs() {
    try {
        const action = document.getElementById('auditFilterAction').value;
        const entityType = document.getElementById('auditFilterEntity').value;
        
        let url = `${API_BASE_URL}/admin/audit-logs?limit=50`;
        if (action) url += `&action=${action}`;
        if (entityType) url += `&entity_type=${entityType}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayAuditLogs(data.logs);
        }
    } catch (error) {
        console.error('Audit logs load error:', error);
        showAlert('Failed to load audit logs', 'error');
    }
}

function displayAuditLogs(logs) {
    const tbody = document.getElementById('auditLogsTableBody');
    
    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No audit logs found</td></tr>';
        return;
    }
    
    tbody.innerHTML = logs.map(log => {
        const date = new Date(log.created_at).toLocaleString();
        return `
            <tr>
                <td>${log.admin}</td>
                <td>${log.action}</td>
                <td>${log.entity_type}</td>
                <td>${date}</td>
                <td>${log.ip_address || '-'}</td>
            </tr>
        `;
    }).join('');
}

// ============================================================================
// Settings
// ============================================================================

async function handleChangePassword(e) {
    e.preventDefault();
    
    const oldPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (newPassword !== confirmPassword) {
        showAlert('Passwords do not match', 'error');
        return;
    }
    
    if (newPassword.length < 8) {
        showAlert('Password must be at least 8 characters', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Password changed successfully', 'success');
            document.getElementById('changePasswordForm').reset();
        } else {
            showAlert(data.message || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showAlert('An error occurred while changing password', 'error');
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    const alertId = 'alert-' + Date.now();
    
    const alert = document.createElement('div');
    alert.id = alertId;
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <i class="material-icons">${type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info'}</i>
        <span>${message}</span>
    `;
    
    container.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// ============================================================================
// Token Management
// ============================================================================

let currentTokenUserId = null;
let currentTokenUserName = null;

function openTokenModal(userId, userName) {
    currentTokenUserId = userId;
    currentTokenUserName = userName;
    
    document.getElementById('tokenUserName').textContent = userName;
    document.getElementById('tokenFile').value = '';
    document.getElementById('tokenUploadError').classList.add('hidden');
    document.getElementById('tokenUploadSuccess').classList.add('hidden');
    
    // Load token info
    loadTokenInfo(userId);
    
    document.getElementById('tokenModal').classList.add('active');
}

function closeTokenModal() {
    document.getElementById('tokenModal').classList.remove('active');
    currentTokenUserId = null;
    currentTokenUserName = null;
}

async function loadTokenInfo(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tokens/users/${userId}/get`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.has_token) {
                const info = data.token_info;
                document.getElementById('tokenStatus').innerHTML = `
                    <span class="badge badge-success">Token Configured</span><br>
                    <small>Type: ${info.type || 'N/A'}</small>
                `;
                document.getElementById('deleteTokenBtn').style.display = 'inline-block';
            } else {
                document.getElementById('tokenStatus').innerHTML = '<span class="badge badge-danger">No Token</span>';
                document.getElementById('deleteTokenBtn').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading token info:', error);
        document.getElementById('tokenStatus').innerHTML = '<span class="badge badge-danger">Error</span>';
    }
}

async function uploadUserToken() {
    const fileInput = document.getElementById('tokenFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('Please select a token file', 'error');
        return;
    }
    
    try {
        // Read file as text
        const fileContent = await file.text();
        
        // Parse JSON to validate
        let tokenJson;
        try {
            tokenJson = JSON.parse(fileContent);
        } catch (e) {
            showAlert('Invalid JSON file', 'error');
            return;
        }
        
        // Upload token
        const response = await fetch(`${API_BASE_URL}/tokens/users/${currentTokenUserId}/set`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({ token_json: tokenJson })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('tokenUploadSuccess').classList.remove('hidden');
            document.getElementById('tokenUploadSuccessMsg').textContent = data.message || 'Token uploaded successfully';
            document.getElementById('tokenUploadError').classList.add('hidden');
            
            showAlert('Token uploaded successfully', 'success');
            
            // Reload token info
            setTimeout(() => {
                loadTokenInfo(currentTokenUserId);
            }, 1000);
        } else {
            document.getElementById('tokenUploadError').classList.remove('hidden');
            document.getElementById('tokenUploadErrorMsg').textContent = data.message || 'Failed to upload token';
            showAlert(data.message || 'Failed to upload token', 'error');
        }
    } catch (error) {
        console.error('Error uploading token:', error);
        document.getElementById('tokenUploadError').classList.remove('hidden');
        document.getElementById('tokenUploadErrorMsg').textContent = 'An error occurred while uploading';
        showAlert('An error occurred while uploading token', 'error');
    }
}

async function deleteUserToken() {
    if (!confirm('Are you sure you want to delete this token?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/tokens/users/${currentTokenUserId}/delete`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Token deleted successfully', 'success');
            loadTokenInfo(currentTokenUserId);
        } else {
            showAlert(data.message || 'Failed to delete token', 'error');
        }
    } catch (error) {
        console.error('Error deleting token:', error);
        showAlert('An error occurred while deleting token', 'error');
    }
}

// ============================================================================
// Initial Load
// ============================================================================

// Load dashboard on page load
window.addEventListener('load', async () => {
    if (sessionToken && currentAdminInfo) {
        await loadDashboard();
    }
});
