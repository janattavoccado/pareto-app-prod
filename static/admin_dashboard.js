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

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Initial UI setup
    showLoginModal(); // Start with login modal

    // Event listeners
    setupEventListeners();

    // Check for existing session token
    if (sessionToken) {
        await validateSession();
    }
});

// ============================================================================
// Theme Management
// ============================================================================

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.className = savedTheme + '-mode';
    document.getElementById('themeToggle').textContent = savedTheme === 'dark' ? 'brightness_7' : 'brightness_4';
}

function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('light-mode', !isDark);
    const newTheme = isDark ? 'dark' : 'light';
    localStorage.setItem('theme', newTheme);
    document.getElementById('themeToggle').textContent = isDark ? 'brightness_7' : 'brightness_4';
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('loginForm').addEventListener('submit', handleLogin);

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
            
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
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

        if (data.success && data.admin) {
            currentAdminInfo = data.admin;
            hideLoginModal();
            updateAdminInfo();
            await loadDashboard();
            navigateToPage('dashboard');
        } else {
            logout(true); // Soft logout, don't show alert
        }
    } catch (error) {
        console.error('Session validation error:', error);
        logout(true); // Soft logout
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
            console.error('Logout API call failed:', error);
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

function showLoginModal() {
    document.getElementById('loginModal').classList.add('active');
    document.querySelector('.container-main').style.display = 'none';
}

function hideLoginModal() {
    document.getElementById('loginModal').classList.remove('active');
    document.querySelector('.container-main').style.display = 'flex';
}

function updateAdminInfo() {
    if (currentAdminInfo) {
        document.getElementById('adminName').textContent = currentAdminInfo.username || 'Admin';
        
        let initials = 'AD'; // Default initials
        if (currentAdminInfo.full_name && typeof currentAdminInfo.full_name === 'string') {
            initials = currentAdminInfo.full_name
                .split(' ')
                .map(n => n[0])
                .join('')
                .toUpperCase();
        } else if (currentAdminInfo.username && typeof currentAdminInfo.username === 'string') {
            initials = currentAdminInfo.username.substring(0, 2).toUpperCase();
        }
        document.getElementById('userAvatar').textContent = initials;
    }
}

// ============================================================================
// Navigation
// ============================================================================

function navigateToPage(page) {
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`[data-page="${page}"]`);
    if (activeItem) activeItem.classList.add('active');

    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) pageElement.classList.remove('hidden');

    // Load data for the page
    const loadFunction = window['load' + page.charAt(0).toUpperCase() + page.slice(1)];
    if (typeof loadFunction === 'function') {
        loadFunction();
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
        const result = await response.json();

        if (result.success && result.data) {
            const stats = result.data.statistics;
            document.getElementById('totalTenants').textContent = stats.tenant_count ?? '0';
            document.getElementById('totalUsers').textContent = stats.user_count ?? '0';
            document.getElementById('totalAdmins').textContent = stats.admin_count ?? '0';

            renderRecentTenants(result.data.recent_tenants);
            renderRecentUsers(result.data.recent_users);
        } else {
            throw new Error(result.message || 'Failed to parse dashboard data');
        }
    } catch (error) {
        console.error('Dashboard load error:', error);
        showAlert('Failed to load dashboard data. Please try again.', 'error');
    }
}

function renderRecentTenants(tenants) {
    const container = document.getElementById('recentTenantsContainer');
    if (!tenants || tenants.length === 0) {
        container.innerHTML = '<p class="empty-state">No recent tenants</p>';
        return;
    }
    let html = '<table class="data-table"><thead><tr><th>Name</th><th>Status</th><th>Created At</th></tr></thead><tbody>';
    tenants.forEach(tenant => {
        const date = tenant.created_at ? new Date(tenant.created_at).toLocaleDateString() : 'N/A';
        const status = tenant.is_active ? '<span class="status-active">Active</span>' : '<span class="status-inactive">Inactive</span>';
        html += `<tr><td>${tenant.name}</td><td>${status}</td><td>${date}</td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderRecentUsers(users) {
    const container = document.getElementById('recentUsersContainer');
    if (!users || users.length === 0) {
        container.innerHTML = '<p class="empty-state">No recent users</p>';
        return;
    }
    let html = '<table class="data-table"><thead><tr><th>Phone Number</th><th>Email</th><th>Status</th></tr></thead><tbody>';
    users.forEach(user => {
        const status = user.is_enabled ? '<span class="status-active">Enabled</span>' : '<span class="status-inactive">Disabled</span>';
        html += `<tr><td>${user.phone_number}</td><td>${user.email || 'N/A'}</td><td>${status}</td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}


// ============================================================================
// Generic Fetch & Utility Functions
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    const config = {
        headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API request to ${endpoint} failed:`, error);
        showAlert(error.message, 'error');
        throw error;
    }
}

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alertContainer.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

// Placeholder functions for other pages to avoid errors if they are not fully implemented
async function loadTenants() { console.log("loadTenants called"); }
async function loadUsers() { console.log("loadUsers called"); }
async function loadAuditLogs() { console.log("loadAuditLogs called"); }
async function loadSettings() { console.log("loadSettings called"); }

// Make sure to implement the full functionality for these pages as needed.
 
 