/**
 * Pareto Admin Dashboard - JavaScript (v3 - Full CRUD)
 * Handles all dashboard functionality, API calls, and UI interactions
 * for Dashboard, Tenants, and Users pages.
 */

const API_BASE_URL = window.location.origin + 
'/api';
let sessionToken = localStorage.getItem('sessionToken');
let currentAdminInfo = null;
let currentEditingId = null; // Used for both tenants and users

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    if (sessionToken) {
        await validateSession();
    } else {
        showLoginModal();
    }
});

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    // Main navigation
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', () => navigateToPage(item.dataset.page));
    });

    // Tenant page
    document.getElementById('addTenantBtn').addEventListener('click', openTenantModal);
    document.getElementById('tenantForm').addEventListener('submit', handleSaveTenant);

    // User page
    document.getElementById('addUserBtn').addEventListener('click', openUserModal);
    document.getElementById('userForm').addEventListener('submit', handleSaveUser);
}

// ============================================================================
// Authentication & Session
// ============================================================================

async function handleLogin(e) {
    e.preventDefault();
    // ... (implementation from previous turn, no changes needed)
}

async function validateSession() {
    // ... (implementation from previous turn, no changes needed)
}

async function logout(soft = false) {
    // ... (implementation from previous turn, no changes needed)
}

function showLoginModal() {
    // ... (implementation from previous turn, no changes needed)
}

function hideLoginModal() {
    // ... (implementation from previous turn, no changes needed)
}

function updateAdminInfo() {
    // ... (implementation from previous turn, no changes needed)
}

// ============================================================================
// Navigation
// ============================================================================

function navigateToPage(page) {
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`).classList.add('active');

    document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
    document.getElementById(`${page}Page`).classList.remove('hidden');

    // Dynamically load data for the selected page
    const loadFunction = window['load' + page.charAt(0).toUpperCase() + page.slice(1)];
    if (typeof loadFunction === 'function') {
        loadFunction();
    }
}

// ============================================================================
// Dashboard Page
// ============================================================================

async function loadDashboard() {
    // ... (implementation from previous turn, no changes needed)
}

// ============================================================================
// Tenants Page
// ============================================================================

async function loadTenants() {
    try {
        const result = await apiRequest('/admin/tenants');
        if (result.success) {
            renderTable('tenantsTable', result.data, ['name', 'is_active'], openTenantModal, deleteTenant);
        }
    } catch (error) {
        showAlert('Failed to load tenants.', 'error');
    }
}

function openTenantModal(tenant = null) {
    currentEditingId = tenant ? tenant.id : null;
    document.getElementById('tenantModalTitle').textContent = tenant ? 'Edit Tenant' : 'Add New Tenant';
    document.getElementById('tenantName').value = tenant ? tenant.name : '';
    document.getElementById('tenantIsActive').checked = tenant ? tenant.is_active : true;
    document.getElementById('tenantModal').classList.add('active');
}

async function handleSaveTenant(e) {
    e.preventDefault();
    const tenantData = {
        name: document.getElementById('tenantName').value,
        is_active: document.getElementById('tenantIsActive').checked,
    };

    const endpoint = currentEditingId ? `/admin/tenants/${currentEditingId}` : '/admin/tenants';
    const method = currentEditingId ? 'PUT' : 'POST';

    try {
        const result = await apiRequest(endpoint, { method, body: JSON.stringify(tenantData) });
        if (result.success) {
            showAlert(`Tenant ${currentEditingId ? 'updated' : 'created'} successfully!`, 'success');
            document.getElementById('tenantModal').classList.remove('active');
            loadTenants(); // Refresh the table
        }
    } catch (error) {
        // Error is already shown by apiRequest
    }
}

async function deleteTenant(tenantId) {
    if (confirm('Are you sure you want to delete this tenant?')) {
        try {
            const result = await apiRequest(`/admin/tenants/${tenantId}`, { method: 'DELETE' });
            if (result.success) {
                showAlert('Tenant deleted successfully!', 'success');
                loadTenants(); // Refresh the table
            }
        } catch (error) {
            // Error is already shown by apiRequest
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
            renderTable('usersTable', result.data, ['phone_number', 'email', 'first_name', 'last_name', 'is_enabled'], openUserModal, deleteUser);
        }
    } catch (error) {
        showAlert('Failed to load users.', 'error');
    }
}

function openUserModal(user = null) {
    currentEditingId = user ? user.id : null;
    document.getElementById('userModalTitle').textContent = user ? 'Edit User' : 'Add New User';
    document.getElementById('userPhoneNumber').value = user ? user.phone_number : '';
    document.getElementById('userEmail').value = user ? user.email : '';
    document.getElementById('userFirstName').value = user ? user.first_name : '';
    document.getElementById('userLastName').value = user ? user.last_name : '';
    document.getElementById('userIsEnabled').checked = user ? user.is_enabled : true;
    // You might need to load tenants into a dropdown here
    document.getElementById('userModal').classList.add('active');
}

async function handleSaveUser(e) {
    e.preventDefault();
    const userData = {
        phone_number: document.getElementById('userPhoneNumber').value,
        email: document.getElementById('userEmail').value,
        first_name: document.getElementById('userFirstName').value,
        last_name: document.getElementById('userLastName').value,
        is_enabled: document.getElementById('userIsEnabled').checked,
        // tenant_id: ... get from a dropdown
    };

    const endpoint = currentEditingId ? `/admin/users/${currentEditingId}` : '/admin/users';
    const method = currentEditingId ? 'PUT' : 'POST';

    try {
        const result = await apiRequest(endpoint, { method, body: JSON.stringify(userData) });
        if (result.success) {
            showAlert(`User ${currentEditingId ? 'updated' : 'created'} successfully!`, 'success');
            document.getElementById('userModal').classList.remove('active');
            loadUsers(); // Refresh the table
        }
    } catch (error) {
        // Error is already shown by apiRequest
    }
}

async function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        try {
            const result = await apiRequest(`/admin/users/${userId}`, { method: 'DELETE' });
            if (result.success) {
                showAlert('User deleted successfully!', 'success');
                loadUsers(); // Refresh the table
            }
        } catch (error) {
            // Error is already shown by apiRequest
        }
    }
}

// ============================================================================
// Generic Helper Functions
// ============================================================================

/**
 * Generic function to render data into a table.
 * @param {string} tableId - The ID of the table body.
 * @param {Array} data - The array of data objects.
 * @param {Array} columns - The keys of the data to display in order.
 * @param {Function} editCallback - Function to call when edit button is clicked.
 * @param {Function} deleteCallback - Function to call when delete button is clicked.
 */
function renderTable(tableId, data, columns, editCallback, deleteCallback) {
    const tbody = document.getElementById(tableId).querySelector('tbody');
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        const colSpan = columns.length + 1; // +1 for actions column
        tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">No data available</td></tr>`;
        return;
    }

    data.forEach(item => {
        const row = document.createElement('tr');
        
        columns.forEach(col => {
            const cell = document.createElement('td');
            cell.textContent = item[col];
            row.appendChild(cell);
        });

        // Actions cell
        const actionsCell = document.createElement('td');
        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.className = 'btn btn-sm btn-secondary';
        editBtn.onclick = () => editCallback(item);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.onclick = () => deleteCallback(item.id);

        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
        row.appendChild(actionsCell);

        tbody.appendChild(row);
    });
}

async function apiRequest(endpoint, options = {}) {
    // ... (implementation from previous turn, no changes needed)
}

function showAlert(message, type = 'info') {
    // ... (implementation from previous turn, no changes needed)
}
