/**
 * Pareto CRM User Portal - JavaScript
 * Handles user authentication and CRM lead management
 */

const API_BASE_URL = window.location.origin + '/api';
let userToken = localStorage.getItem('userCrmToken');
let currentUser = null;
let currentLeadId = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Check if logged in
    if (userToken) {
        await validateUserSession();
    }
    
    // Event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Login form
    document.getElementById('userLoginForm').addEventListener('submit', handleUserLogin);
    
    // Password setup
    document.getElementById('setupPasswordLink').addEventListener('click', (e) => {
        e.preventDefault();
        closeModal('loginModal');
        openModal('passwordSetupModal');
    });
    document.getElementById('passwordSetupForm').addEventListener('submit', handlePasswordSetup);
    
    // Logout
    document.getElementById('userLogoutBtn').addEventListener('click', handleUserLogout);
    
    // Filters
    document.getElementById('userStatusFilter').addEventListener('change', loadUserLeads);
    document.getElementById('userPriorityFilter').addEventListener('change', loadUserLeads);
    document.getElementById('userMyLeadsOnly').addEventListener('change', loadUserLeads);
}

// ============================================================================
// Authentication
// ============================================================================

async function handleUserLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    hideError('loginError');
    
    try {
        const response = await fetch(`${API_BASE_URL}/user/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            userToken = data.session_token;
            localStorage.setItem('userCrmToken', userToken);
            currentUser = data.user;
            showMainContent();
        } else {
            showError('loginError', data.message || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('loginError', 'Login failed. Please try again.');
    }
}

async function handlePasswordSetup(e) {
    e.preventDefault();
    
    const email = document.getElementById('setupEmail').value;
    const password = document.getElementById('setupPassword').value;
    const confirmPassword = document.getElementById('setupConfirmPassword').value;
    
    hideError('setupError');
    
    if (password !== confirmPassword) {
        showError('setupError', 'Passwords do not match');
        return;
    }
    
    if (password.length < 8) {
        showError('setupError', 'Password must be at least 8 characters');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/user/setup-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Password set successfully! You can now login.', 'success');
            closeModal('passwordSetupModal');
            openModal('loginModal');
            document.getElementById('loginEmail').value = email;
        } else {
            showError('setupError', data.message || 'Failed to set password');
        }
    } catch (error) {
        console.error('Password setup error:', error);
        showError('setupError', 'Failed to set password. Please try again.');
    }
}

async function validateUserSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/validate`, {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            showMainContent();
        } else {
            handleUserLogout();
        }
    } catch (error) {
        console.error('Session validation error:', error);
        handleUserLogout();
    }
}

function handleUserLogout() {
    userToken = null;
    currentUser = null;
    localStorage.removeItem('userCrmToken');
    
    document.getElementById('mainContainer').style.display = 'none';
    document.getElementById('userNavRight').style.display = 'none';
    openModal('loginModal');
}

function showMainContent() {
    closeModal('loginModal');
    closeModal('passwordSetupModal');
    
    document.getElementById('mainContainer').style.display = 'block';
    document.getElementById('userNavRight').style.display = 'flex';
    
    // Update user info
    if (currentUser) {
        const displayName = currentUser.full_name || currentUser.email.split('@')[0];
        document.getElementById('userDisplayName').textContent = displayName;
        document.getElementById('userAvatarInitial').textContent = displayName.charAt(0).toUpperCase();
        document.getElementById('tenantDisplayName').textContent = currentUser.tenant_name || '';
    }
    
    loadUserLeads();
}

// ============================================================================
// CRM Leads
// ============================================================================

async function loadUserLeads() {
    const status = document.getElementById('userStatusFilter').value;
    const priority = document.getElementById('userPriorityFilter').value;
    const myLeadsOnly = document.getElementById('userMyLeadsOnly').checked;
    
    let url = `${API_BASE_URL}/crm/leads?`;
    if (status) url += `status=${status}&`;
    if (priority) url += `priority=${priority}&`;
    if (myLeadsOnly) url += `my_leads=true&`;
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayUserLeads(data.leads || []);
            updateUserStats(data.stats || {});
        } else {
            showAlert(data.message || 'Failed to load leads', 'error');
        }
    } catch (error) {
        console.error('Error loading leads:', error);
        showAlert('Failed to load leads', 'error');
    }
}

function displayUserLeads(leads) {
    const container = document.getElementById('leadsContainer');
    
    if (leads && leads.length > 0) {
        container.innerHTML = leads.map(lead => {
            const priorityClass = lead.priority === 'High' ? 'badge-danger' : 
                                  lead.priority === 'Mid' ? 'badge-warning' : 'badge-info';
            const statusClass = lead.status === 'Open' ? 'badge-primary' :
                               lead.status === 'In Progress' ? 'badge-warning' :
                               lead.status === 'Closed' ? 'badge-success' : 'badge-secondary';
            
            return `
                <div class="lead-card" onclick="viewLead(${lead.id})">
                    <div class="lead-subject">${lead.lead_subject || 'No Subject'}</div>
                    <div class="lead-meta">
                        <span><i class="material-icons" style="font-size: 14px; vertical-align: middle;">person</i> ${lead.owner || '-'}</span>
                        <span class="badge ${priorityClass}">${lead.priority || '-'}</span>
                        <span class="badge ${statusClass}">${lead.status || '-'}</span>
                        <span><i class="material-icons" style="font-size: 14px; vertical-align: middle;">schedule</i> ${lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '-'}</span>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #7f8c8d;">No leads found</div>';
    }
}

function updateUserStats(stats) {
    document.getElementById('userCrmTotal').textContent = stats.total || 0;
    document.getElementById('userCrmOpen').textContent = stats.open || 0;
    document.getElementById('userCrmInProgress').textContent = stats.in_progress || 0;
    document.getElementById('userCrmMine').textContent = stats.my_leads || 0;
}

async function viewLead(leadId) {
    try {
        const response = await fetch(`${API_BASE_URL}/crm/leads/${leadId}`, {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        
        const data = await response.json();
        
        if (data.success && data.lead) {
            const lead = data.lead;
            currentLeadId = lead.id;
            
            document.getElementById('leadDetailId').value = lead.id;
            document.getElementById('leadDetailSubject').textContent = lead.lead_subject || 'No Subject';
            document.getElementById('leadDetailCreatedBy').textContent = lead.user_name || '-';
            document.getElementById('leadDetailOwner').value = lead.owner || '';
            document.getElementById('leadDetailStatus').value = lead.status || 'Open';
            
            // Priority select
            document.getElementById('leadDetailPriority').value = lead.priority || 'Mid';
            
            // Content
            let contentHtml = '';
            if (lead.lead_content) {
                if (typeof lead.lead_content === 'object') {
                    contentHtml = JSON.stringify(lead.lead_content, null, 2);
                } else {
                    contentHtml = lead.lead_content;
                }
            }
            document.getElementById('leadDetailContent').textContent = contentHtml || 'No content';
            
            // Actions
            const actionsGroup = document.getElementById('leadDetailActionsGroup');
            const actionsEl = document.getElementById('leadDetailActions');
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
            
            openModal('leadDetailModal');
        } else {
            showAlert(data.message || 'Failed to load lead details', 'error');
        }
    } catch (error) {
        console.error('Error loading lead:', error);
        showAlert('Failed to load lead details', 'error');
    }
}

async function updateLead() {
    if (!currentLeadId) return;
    
    const newStatus = document.getElementById('leadDetailStatus').value;
    const newOwner = document.getElementById('leadDetailOwner').value;
    const newPriority = document.getElementById('leadDetailPriority').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/crm/leads/${currentLeadId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({ 
                status: newStatus,
                owner: newOwner,
                priority: newPriority
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Lead updated successfully!', 'success');
            closeModal('leadDetailModal');
            loadUserLeads();
        } else {
            showAlert(data.message || 'Failed to update lead', 'error');
        }
    } catch (error) {
        console.error('Error updating lead:', error);
        showAlert('Failed to update lead', 'error');
    }
}

// ============================================================================
// Utilities
// ============================================================================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    el.classList.remove('hidden');
    el.querySelector('span').textContent = message;
}

function hideError(elementId) {
    document.getElementById(elementId).classList.add('hidden');
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
    
    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 5000);
}
