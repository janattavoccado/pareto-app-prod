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

    // Tenant management
    document.getElementById('addTenantBtn').addEventListener('click', openAddTenantModal);
    document.getElementById('tenantForm').addEventListener('submit', handleSaveTenant);
    
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
            document.querySelector('.container-main').style.display = 'flex';
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
            document.querySelector('.container-main').style.display = 'flex';
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
            const stats = data.statistics;
            document.getElementById('totalTenants').textContent = stats.total_tenants;
            document.getElementById('totalUsers').textContent = stats.total_users;
            document.getElementById('activeUsers').textContent = stats.active_users;
            document.getElementById('totalAdmins').textContent = stats.total_admins;
            
            displayRecentActivity(data.recent_activity);
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showAlert('Failed to load dashboard data', 'error');
    }
}

function displayRecentActivity(activity) {
    const container = document.getElementById('recentActivityContainer');
    if (activity && activity.length > 0) {
        container.innerHTML = activity.map(log => `
            <div class="activity-item">
                <span class="activity-time">${new Date(log.created_at).toLocaleString()}</span>
                <span class="activity-admin">${log.admin}</span>
                <span class="activity-action">${log.action}</span>
                <span class="activity-entity">${log.entity_type} ${log.entity_id || ''}</span>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p style="text-align: center; color: #7f8c8d;">No recent activity</p>';
    }
}

// ============================================================================
// User Management
// ============================================================================

async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            displayUsers(data.users);
            await loadTenantsForDropdown();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('Failed to load users', 'error');
    }
}

function displayUsers(users) {
    const tableBody = document.getElementById('usersTableBody');
    tableBody.innerHTML = users.map(user => {
        // Escape single quotes in names for onclick handler
        const escapedName = `${user.first_name} ${user.last_name}`.replace(/'/g, "\\'");
        const tokenUpdatedAt = user.google_token_updated_at || null;
        const calendarDisplay = user.google_calendar_id 
            ? `<span class="badge badge-info" title="${user.google_calendar_id}">${user.google_calendar_id.length > 15 ? user.google_calendar_id.substring(0, 15) + '...' : user.google_calendar_id}</span>` 
            : '<span class="badge badge-secondary">Not Set</span>';
        
        return `
        <tr data-user-id="${user.id}">
            <td>${user.first_name} ${user.last_name}</td>
            <td>${user.phone_number}</td>
            <td>${user.email || '-'}</td>
            <td>${calendarDisplay}</td>
            <td>
                <span class="badge ${user.is_enabled ? 'badge-success' : 'badge-danger'}">${user.is_enabled ? 'Enabled' : 'Disabled'}</span>
            </td>
            <td>
                <button class="btn btn-small ${user.has_token ? 'btn-success' : 'btn-secondary'}" onclick="openTokenModal(${user.id}, '${escapedName}', ${user.has_token}, ${tokenUpdatedAt ? `'${tokenUpdatedAt}'` : 'null'})">
                    ${user.has_token ? 'Manage' : 'Upload'}
                </button>
            </td>
            <td>
                <button class="btn btn-small btn-info" onclick="openEditUserModal(${user.id})">Edit</button>
                <button class="btn btn-small btn-danger" onclick="confirmDeleteUser(${user.id})">Delete</button>
            </td>
        </tr>
    `;
    }).join('');
}

function filterUsers() {
    // Implement filtering logic here if needed
}

async function openAddUserModal() {
    currentEditingUserId = null;
    document.getElementById('userModalTitle').textContent = 'Add User';
    document.getElementById('userForm').reset();
    openModal('userModal');
}

async function openEditUserModal(userId) {
    currentEditingUserId = userId;
    document.getElementById('userModalTitle').textContent = 'Edit User';
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            const user = data.user;
            document.getElementById('userTenant').value = user.tenant_id;
            document.getElementById('userFirstName').value = user.first_name;
            document.getElementById('userLastName').value = user.last_name;
            document.getElementById('userPhone').value = user.phone_number;
            document.getElementById('userEmail').value = user.email || '';
            document.getElementById('userCalendarId').value = user.google_calendar_id || '';
            document.getElementById('userEnabled').checked = user.is_enabled;
            openModal('userModal');
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error fetching user details:', error);
        showAlert('Failed to load user details', 'error');
    }
}

async function handleSaveUser(e) {
    e.preventDefault();
    
    const userData = {
        tenant_id: parseInt(document.getElementById('userTenant').value),
        first_name: document.getElementById('userFirstName').value,
        last_name: document.getElementById('userLastName').value,
        phone_number: document.getElementById('userPhone').value,
        email: document.getElementById('userEmail').value,
        google_calendar_id: document.getElementById('userCalendarId').value || null,
        is_enabled: document.getElementById('userEnabled').checked
    };
    
    const url = currentEditingUserId 
        ? `${API_BASE_URL}/admin/users/${currentEditingUserId}`
        : `${API_BASE_URL}/admin/users`;
    
    const method = currentEditingUserId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify(userData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`User ${currentEditingUserId ? 'updated' : 'created'} successfully!`, 'success');
            closeModal('userModal');
            loadUsers();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        showAlert('Failed to save user', 'error');
    }
}

function confirmDeleteUser(userId) {
    currentDeleteTarget = { type: 'user', id: userId };
    document.getElementById('deleteConfirmMessage').textContent = 'Are you sure you want to delete this user?';
    openModal('deleteConfirmModal');
}

// ============================================================================
// Tenant Management
// ============================================================================

async function loadTenants() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/tenants`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            tenants = data.tenants;
            displayTenants(tenants);
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading tenants:', error);
        showAlert('Failed to load tenants', 'error');
    }
}

function displayTenants(tenantsList) {
    const tableBody = document.getElementById('tenantsTableBody');
    tableBody.innerHTML = tenantsList.map(tenant => `
        <tr>
            <td>${tenant.company_name}</td>
            <td>${tenant.email || '-'}</td>
            <td>${tenant.phone || '-'}</td>
            <td>${tenant.user_count !== undefined ? tenant.user_count : 'N/A'}</td>
            <td>
                <span class="badge ${tenant.active ? 'badge-success' : 'badge-danger'}">${tenant.active ? 'Active' : 'Inactive'}</span>
            </td>
            <td>
                <button class="btn btn-small btn-info" onclick="openEditTenantModal(${tenant.id})">Edit</button>
                <button class="btn btn-small btn-secondary" onclick="viewTenantUsers(${tenant.id})">View Users</button>
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
            const users = data.tenant.users;
            let message = `<strong>${data.tenant.company_name}</strong><br><br>`;
            if (users && users.length > 0) {
                message += `<strong>Users (${users.length}):</strong><br>`;
                message += users.map(u => `${u.first_name} ${u.last_name} (${u.phone_number})`).join('<br>');
            } else {
                message += 'No users found for this tenant.';
            }
            
            showAlert(message, 'info');
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error viewing tenant users:', error);
        showAlert('Failed to load tenant users', 'error');
    }
}

async function loadTenantsForDropdown() {
    if (tenants.length === 0) {
        await loadTenants();
    }
    
    const select = document.getElementById('userTenant');
    select.innerHTML = tenants.map(t => `<option value="${t.id}">${t.company_name}</option>`).join('');
}

function openAddTenantModal() {
    document.getElementById('tenantModalTitle').textContent = 'Add Tenant';
    document.getElementById('tenantId').value = '';
    document.getElementById('companyName').value = '';
    document.getElementById('companySlug').value = '';
    document.getElementById('tenantEmail').value = '';
    document.getElementById('tenantPhone').value = '';
    document.getElementById('tenantActive').value = 'true';
    openModal('tenantModal');
}

function openEditTenantModal(tenantId) {
    document.getElementById('tenantModalTitle').textContent = 'Edit Tenant';
    const tenant = tenants.find(t => t.id === tenantId);
    if (tenant) {
        document.getElementById('tenantId').value = tenant.id;
        document.getElementById('companyName').value = tenant.company_name;
        document.getElementById('companySlug').value = tenant.company_slug;
        document.getElementById('tenantEmail').value = tenant.email || '';
        document.getElementById('tenantPhone').value = tenant.phone || '';
        document.getElementById('tenantActive').value = tenant.active ? 'true' : 'false';
        openModal('tenantModal');
    }
}

async function handleSaveTenant(e) {
    e.preventDefault();
    
    const tenantId = document.getElementById('tenantId').value;
    const tenantData = {
        company_name: document.getElementById('companyName').value,
        company_slug: document.getElementById('companySlug').value,
        email: document.getElementById('tenantEmail').value,
        phone: document.getElementById('tenantPhone').value,
        is_active: document.getElementById('tenantActive').value === 'true'
    };
    
    const isNewTenant = !tenantId;
    const url = isNewTenant 
        ? `${API_BASE_URL}/admin/tenants`
        : `${API_BASE_URL}/admin/tenants/${tenantId}`;
    const method = isNewTenant ? 'POST' : 'PUT';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify(tenantData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`Tenant ${isNewTenant ? 'created' : 'updated'} successfully!`, 'success');
            closeModal('tenantModal');
            loadTenants();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error saving tenant:', error);
        showAlert('Failed to save tenant', 'error');
    }
}

// ============================================================================
// Token Management
// ============================================================================

let currentTokenUserId = null;
let currentTokenUserHasToken = false;
let currentTokenUserData = null;

async function openTokenModal(userId, userName, hasToken, tokenUpdatedAt) {
    currentTokenUserId = userId;
    currentEditingUserId = userId;
    currentTokenUserHasToken = hasToken;
    
    document.getElementById('tokenUserName').textContent = userName;
    document.getElementById('tokenFile').value = '';
    
    // Show/hide token info sections based on whether token exists
    const currentTokenInfo = document.getElementById('currentTokenInfo');
    const noTokenInfo = document.getElementById('noTokenInfo');
    
    if (hasToken) {
        currentTokenInfo.style.display = 'block';
        noTokenInfo.style.display = 'none';
        
        // Set last updated time
        const lastUpdated = tokenUpdatedAt ? new Date(tokenUpdatedAt).toLocaleString() : 'Unknown';
        document.getElementById('tokenLastUpdated').textContent = lastUpdated;
        document.getElementById('tokenStatus').textContent = 'Active';
    } else {
        currentTokenInfo.style.display = 'none';
        noTokenInfo.style.display = 'block';
    }
    
    openModal('tokenModal');
}

async function downloadCurrentToken() {
    if (!currentTokenUserId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${currentTokenUserId}/token`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success && data.token_data) {
            // Create a downloadable JSON file
            const blob = new Blob([JSON.stringify(data.token_data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `google_token_user_${currentTokenUserId}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showAlert('Token downloaded successfully!', 'success');
        } else {
            showAlert(data.message || 'Failed to download token', 'error');
        }
    } catch (error) {
        console.error('Error downloading token:', error);
        showAlert('Failed to download token', 'error');
    }
}

async function deleteCurrentToken() {
    if (!currentTokenUserId) return;
    
    if (!confirm('Are you sure you want to delete this token? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${currentTokenUserId}/token`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Token deleted successfully!', 'success');
            closeModal('tokenModal');
            loadUsers();
        } else {
            showAlert(data.message || 'Failed to delete token', 'error');
        }
    } catch (error) {
        console.error('Error deleting token:', error);
        showAlert('Failed to delete token', 'error');
    }
}

async function handleTokenUpload() {
    const fileInput = document.getElementById('tokenFile');
    if (fileInput.files.length === 0) {
        showAlert('Please select a file', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('token_file', file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${currentEditingUserId}/token`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${sessionToken}` },
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Token uploaded successfully!', 'success');
            closeModal('tokenModal');
            loadUsers();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error uploading token:', error);
        showAlert('Failed to upload token', 'error');
    }
}

// ============================================================================
// Settings
// ============================================================================

async function handleChangePassword(e) {
    e.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmNewPassword = document.getElementById('confirmNewPassword').value;
    
    if (newPassword !== confirmNewPassword) {
        showAlert('New passwords do not match', 'error');
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
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Password changed successfully!', 'success');
            document.getElementById('changePasswordForm').reset();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showAlert('Failed to change password', 'error');
    }
}

// ============================================================================
// Audit Logs
// ============================================================================

async function loadAuditLogs() {
    const action = document.getElementById('auditFilterAction').value;
    const entity = document.getElementById('auditFilterEntity').value;
    
    let url = `${API_BASE_URL}/admin/audit-logs?`;
    if (action) url += `action=${action}&`;
    if (entity) url += `entity_type=${entity}&`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            displayAuditLogs(data.logs);
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading audit logs:', error);
        showAlert('Failed to load audit logs', 'error');
    }
}

function displayAuditLogs(logs) {
    const tableBody = document.getElementById('auditLogsTableBody');
    if (logs && logs.length > 0) {
        tableBody.innerHTML = logs.map(log => `
            <tr>
                <td>${log.admin}</td>
                <td>${log.action}</td>
                <td>${log.entity_type} ${log.entity_id || ''}</td>
                <td>${new Date(log.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } else {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No logs found</td></tr>';
    }
}

// ============================================================================
// Generic Deletion
// ============================================================================

async function confirmDelete() {
    if (!currentDeleteTarget) return;
    
    const { type, id } = currentDeleteTarget;
    const url = `${API_BASE_URL}/admin/${type}s/${id}`;
    
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`${type.charAt(0).toUpperCase() + type.slice(1)} deleted successfully!`, 'success');
            if (type === 'user') {
                loadUsers();
            }
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error(`Error deleting ${type}:`, error);
        showAlert(`Failed to delete ${type}`, 'error');
    }
    
    closeModal('deleteConfirmModal');
    currentDeleteTarget = null;
}

// ============================================================================
// Modal & Alert Utilities
// ============================================================================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check_circle';
    else if (type === 'error') icon = 'error';
    else if (type === 'warning') icon = 'warning';
    
    alert.innerHTML = `
        <i class="material-icons">${icon}</i>
        <span>${message}</span>
        <button class="close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 5000);
}


// ============================================================================
// CRM Management
// ============================================================================

let crmLeads = [];
let currentCrmLeadId = null;

async function loadCrmLeads() {
    const tenantId = document.getElementById('crmTenantFilter').value;
    const status = document.getElementById('crmStatusFilter').value;
    const priority = document.getElementById('crmPriorityFilter').value;
    
    let url = `${API_BASE_URL}/admin/crm/leads?`;
    if (tenantId) url += `tenant_id=${tenantId}&`;
    if (status) url += `status=${status}&`;
    if (priority) url += `priority=${priority}&`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            crmLeads = data.leads || [];
            displayCrmLeads(crmLeads);
            updateCrmStats(data.stats || {});
        } else {
            showAlert(data.message || 'Failed to load CRM leads', 'error');
        }
    } catch (error) {
        console.error('Error loading CRM leads:', error);
        showAlert('Failed to load CRM leads', 'error');
    }
}

function displayCrmLeads(leads) {
    const tableBody = document.getElementById('crmLeadsTableBody');
    
    if (leads && leads.length > 0) {
        tableBody.innerHTML = leads.map(lead => {
            const priorityClass = lead.priority === 'High' ? 'badge-danger' : 
                                  lead.priority === 'Mid' ? 'badge-warning' : 'badge-info';
            const statusClass = lead.status === 'Open' ? 'badge-primary' :
                               lead.status === 'In Progress' ? 'badge-warning' :
                               lead.status === 'Closed' ? 'badge-success' : 'badge-secondary';
            
            return `
                <tr>
                    <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${lead.lead_subject || 'No Subject'}
                    </td>
                    <td>${lead.tenant_name || '-'}</td>
                    <td>${lead.user_name || '-'}</td>
                    <td>${lead.owner || '-'}</td>
                    <td><span class="badge ${priorityClass}">${lead.priority || '-'}</span></td>
                    <td><span class="badge ${statusClass}">${lead.status || '-'}</span></td>
                    <td>${lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                        <button class="btn btn-small btn-info" onclick="viewCrmLead(${lead.id})">
                            <i class="material-icons" style="font-size: 16px;">visibility</i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } else {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No leads found</td></tr>';
    }
}

function updateCrmStats(stats) {
    document.getElementById('crmTotalLeads').textContent = stats.total || 0;
    document.getElementById('crmOpenLeads').textContent = stats.open || 0;
    document.getElementById('crmInProgressLeads').textContent = stats.in_progress || 0;
    document.getElementById('crmHighPriorityLeads').textContent = stats.high_priority || 0;
}

async function loadCrmTenantFilter() {
    // Populate tenant filter dropdown
    const select = document.getElementById('crmTenantFilter');
    select.innerHTML = '<option value="">All Tenants</option>';
    
    tenants.forEach(tenant => {
        const option = document.createElement('option');
        option.value = tenant.id;
        option.textContent = tenant.company_name || tenant.name;
        select.appendChild(option);
    });
}

async function viewCrmLead(leadId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/crm/leads/${leadId}`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        const data = await response.json();
        
        if (data.success && data.lead) {
            const lead = data.lead;
            currentCrmLeadId = lead.id;
            
            document.getElementById('crmLeadId').value = lead.id;
            document.getElementById('crmLeadSubject').textContent = lead.lead_subject || 'No Subject';
            document.getElementById('crmLeadTenant').textContent = lead.tenant_name || '-';
            document.getElementById('crmLeadCreatedBy').textContent = lead.user_name || '-';
            document.getElementById('crmLeadOwner').textContent = lead.owner || '-';
            document.getElementById('crmLeadStatus').value = lead.status || 'Open';
            document.getElementById('crmLeadCreated').textContent = lead.created_at ? 
                new Date(lead.created_at).toLocaleString() : '-';
            
            // Priority badge
            const priorityEl = document.getElementById('crmLeadPriority');
            priorityEl.textContent = lead.priority || '-';
            priorityEl.className = 'badge ' + (
                lead.priority === 'High' ? 'badge-danger' : 
                lead.priority === 'Mid' ? 'badge-warning' : 'badge-info'
            );
            
            // Content
            let contentHtml = '';
            if (lead.lead_content) {
                if (typeof lead.lead_content === 'object') {
                    contentHtml = JSON.stringify(lead.lead_content, null, 2);
                } else {
                    contentHtml = lead.lead_content;
                }
            }
            document.getElementById('crmLeadContent').textContent = contentHtml || 'No content';
            
            // Actions
            const actionsGroup = document.getElementById('crmLeadActionsGroup');
            const actionsEl = document.getElementById('crmLeadActions');
            if (lead.action && (typeof lead.action === 'object' ? Object.keys(lead.action).length > 0 : lead.action)) {
                actionsGroup.style.display = 'block';
                if (typeof lead.action === 'object') {
                    actionsEl.textContent = JSON.stringify(lead.action, null, 2);
                } else {
                    actionsEl.textContent = lead.action;
                }
            } else {
                actionsGroup.style.display = 'none';
            }
            
            openModal('crmLeadModal');
        } else {
            showAlert(data.message || 'Failed to load lead details', 'error');
        }
    } catch (error) {
        console.error('Error loading CRM lead:', error);
        showAlert('Failed to load lead details', 'error');
    }
}

async function updateCrmLeadStatus() {
    if (!currentCrmLeadId) return;
    
    const newStatus = document.getElementById('crmLeadStatus').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/crm/leads/${currentCrmLeadId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Lead status updated successfully!', 'success');
            closeModal('crmLeadModal');
            loadCrmLeads();
        } else {
            showAlert(data.message || 'Failed to update lead status', 'error');
        }
    } catch (error) {
        console.error('Error updating CRM lead:', error);
        showAlert('Failed to update lead status', 'error');
    }
}

// Add CRM filter event listeners
document.addEventListener('DOMContentLoaded', () => {
    // CRM filters
    const crmTenantFilter = document.getElementById('crmTenantFilter');
    const crmStatusFilter = document.getElementById('crmStatusFilter');
    const crmPriorityFilter = document.getElementById('crmPriorityFilter');
    
    if (crmTenantFilter) crmTenantFilter.addEventListener('change', loadCrmLeads);
    if (crmStatusFilter) crmStatusFilter.addEventListener('change', loadCrmLeads);
    if (crmPriorityFilter) crmPriorityFilter.addEventListener('change', loadCrmLeads);
});

// Override navigateToPage to include CRM
const originalNavigateToPage = navigateToPage;
navigateToPage = function(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    
    // Update sidebar active state
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });
    
    // Show selected page and load data
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) {
        pageElement.classList.remove('hidden');
    }
    
    // Load page-specific data
    switch (page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'users':
            loadUsers();
            break;
        case 'tenants':
            loadTenants();
            break;
        case 'crm':
            loadCrmTenantFilter();
            loadCrmLeads();
            break;
        case 'audit-logs':
            loadAuditLogs();
            break;
    }
};
