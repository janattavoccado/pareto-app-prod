"""
Admin Management Routes

Provides Flask endpoints for:
- User management (CRUD)
- Tenant management (CRUD)
- Audit log viewing
- Admin dashboard

File location: pareto_agents/admin_routes.py
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from .auth import require_auth
from .database import get_db_session, User, Tenant, AuditLog, Administrator

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ============================================================================
# Audit Logging Helper
# ============================================================================

def log_audit(admin_id: int, action: str, entity_type: str, entity_id: int = None, changes: dict = None, ip_address: str = None):
    """
    Log an administrative action
    
    Args:
        admin_id: Administrator ID
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        entity_type: Type of entity (USER, TENANT, ADMIN)
        entity_id: ID of affected entity
        changes: Dictionary of changes
        ip_address: Client IP address
    """
    session = get_db_session()
    try:
        audit_log = AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=json.dumps(changes) if changes else None,
            ip_address=ip_address
        )
        session.add(audit_log)
        session.commit()
    except Exception as e:
        logger.error(f"Error logging audit: {e}")
    finally:
        session.close()


# ============================================================================
# Dashboard Routes
# ============================================================================

@admin_bp.route('/dashboard', methods=['GET'])
@require_auth
def dashboard():
    """
    Admin dashboard overview
    
    Response:
    {
        "admin": {...},
        "statistics": {
            "total_tenants": 1,
            "total_users": 3,
            "active_users": 1,
            "total_admins": 1
        },
        "recent_activity": [...]
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            # Get statistics
            tenant_count = session.query(Tenant).filter_by(is_active=True).count()
            user_count = session.query(User).count()
            active_user_count = session.query(User).filter_by(is_enabled=True).count()
            admin_count = session.query(Administrator).filter_by(is_active=True).count()
            
            # Get recent activity
            recent_logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
            
            activity = []
            for log in recent_logs:
                activity.append({
                    'id': log.id,
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'created_at': log.created_at.isoformat(),
                    'admin': log.administrator.username if log.administrator else 'System'
                })
            
            logger.info(f"✅ Dashboard accessed by {admin_info['username']}")
            
            return jsonify({
                'success': True,
                'admin': admin_info,
                'statistics': {
                    'total_tenants': tenant_count,
                    'total_users': user_count,
                    'active_users': active_user_count,
                    'total_admins': admin_count
                },
                'recent_activity': activity
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# User Management Routes
# ============================================================================

@admin_bp.route('/users', methods=['GET'])
@require_auth
def list_users():
    """
    List all users
    
    Query parameters:
    - tenant_id: Filter by tenant (optional)
    - enabled: Filter by enabled status (true/false)
    
    Response:
    {
        "success": true,
        "users": [...]
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            # Get query parameters
            tenant_id = request.args.get('tenant_id', type=int)
            enabled = request.args.get('enabled')
            
            # Build query
            query = session.query(User)
            
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            if enabled is not None:
                enabled_bool = enabled.lower() == 'true'
                query = query.filter_by(is_enabled=enabled_bool)
            
            users = query.all()
            
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'tenant_id': user.tenant_id,
                    'phone_number': user.phone_number,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.full_name,
                    'email': user.email,
                    'enabled': user.is_enabled,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                })
            
            logger.info(f"✅ Listed {len(users)} users")
            
            return jsonify({
                'success': True,
                'count': len(users_data),
                'users': users_data
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ List users error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """
    Get user details
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            user_data = {
                'id': user.id,
                'tenant_id': user.tenant_id,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'email': user.email,
                'enabled': user.is_enabled,
                'google_token_path': user.google_token_path,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
            
            logger.info(f"✅ Retrieved user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'user': user_data
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Get user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users', methods=['POST'])
@require_auth
def create_user():
    """
    Create a new user
    
    Request body:
    {
        "tenant_id": 1,
        "phone_number": "+46701234567",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "enabled": true,
        "google_token_path": "path/to/token.json"
    }
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['tenant_id', 'phone_number', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        session = get_db_session()
        
        try:
            # Check if user already exists
            existing = session.query(User).filter_by(
                tenant_id=data['tenant_id'],
                phone_number=data['phone_number']
            ).first()
            
            if existing:
                logger.warning(f"❌ User already exists: {data['phone_number']}")
                return jsonify({'success': False, 'message': 'User already exists'}), 409
            
            # Create user
            user = User(
                tenant_id=data['tenant_id'],
                phone_number=data['phone_number'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data.get('email'),
                is_enabled=data.get('enabled', True),
                google_token_path=data.get('google_token_path')
            )
            
            session.add(user)
            session.commit()
            
            # Log audit
            log_audit(
                admin_id=admin_info['admin_id'],
                action='CREATE',
                entity_type='USER',
                entity_id=user.id,
                changes={'created': data},
                ip_address=request.remote_addr
            )
            
            logger.info(f"✅ Created user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name
                }
            }), 201
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Create user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """
    Update user information
    
    Request body:
    {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "enabled": false
    }
    
    Response:
    {
        "success": true,
        "user": {...}
    }
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Track changes
            changes = {}
            
            # Update fields
            if 'first_name' in data:
                changes['first_name'] = {'old': user.first_name, 'new': data['first_name']}
                user.first_name = data['first_name']
            
            if 'last_name' in data:
                changes['last_name'] = {'old': user.last_name, 'new': data['last_name']}
                user.last_name = data['last_name']
            
            if 'email' in data:
                changes['email'] = {'old': user.email, 'new': data['email']}
                user.email = data['email']
            
            if 'enabled' in data:
                changes['enabled'] = {'old': user.is_enabled, 'new': data['enabled']}
                user.is_enabled = data['enabled']
            
            if 'google_token_path' in data:
                changes['google_token_path'] = {'old': user.google_token_path, 'new': data['google_token_path']}
                user.google_token_path = data['google_token_path']
            
            session.commit()
            
            # Log audit
            if changes:
                log_audit(
                    admin_id=admin_info['admin_id'],
                    action='UPDATE',
                    entity_type='USER',
                    entity_id=user.id,
                    changes=changes,
                    ip_address=request.remote_addr
                )
            
            logger.info(f"✅ Updated user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': {
                    'id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name,
                    'email': user.email,
                    'enabled': user.is_enabled
                }
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Update user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    """
    Delete a user
    
    Response:
    {
        "success": true,
        "message": "User deleted successfully"
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            user_name = user.full_name
            session.delete(user)
            session.commit()
            
            # Log audit
            log_audit(
                admin_id=admin_info['admin_id'],
                action='DELETE',
                entity_type='USER',
                entity_id=user_id,
                changes={'deleted': user_name},
                ip_address=request.remote_addr
            )
            
            logger.info(f"✅ Deleted user: {user_name}")
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Delete user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# Tenant Management Routes
# ============================================================================

@admin_bp.route('/tenants', methods=['GET'])
@require_auth
def list_tenants():
    """
    List all tenants
    
    Response:
    {
        "success": true,
        "tenants": [...]
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            tenants = session.query(Tenant).all()
            
            tenants_data = []
            for tenant in tenants:
                user_count = session.query(User).filter_by(tenant_id=tenant.id).count()
                tenants_data.append({
                    'id': tenant.id,
                    'company_name': tenant.company_name,
                    'company_slug': tenant.company_slug,
                    'email': tenant.email,
                    'phone': tenant.phone,
                    'active': tenant.is_active,
                    'user_count': user_count,
                    'created_at': tenant.created_at.isoformat() if tenant.created_at else None
                })
            
            logger.info(f"✅ Listed {len(tenants)} tenants")
            
            return jsonify({
                'success': True,
                'count': len(tenants_data),
                'tenants': tenants_data
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ List tenants error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['GET'])
@require_auth
def get_tenant(tenant_id):
    """
    Get tenant details with users
    
    Response:
    {
        "success": true,
        "tenant": {...},
        "users": [...]
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            
            if not tenant:
                logger.warning(f"❌ Tenant not found: {tenant_id}")
                return jsonify({'success': False, 'message': 'Tenant not found'}), 404
            
            users = session.query(User).filter_by(tenant_id=tenant_id).all()
            
            tenant_data = {
                'id': tenant.id,
                'company_name': tenant.company_name,
                'company_slug': tenant.company_slug,
                'email': tenant.email,
                'phone': tenant.phone,
                'active': tenant.is_active,
                'created_at': tenant.created_at.isoformat() if tenant.created_at else None
            }
            
            users_data = [{
                'id': u.id,
                'phone_number': u.phone_number,
                'full_name': u.full_name,
                'enabled': u.is_enabled
            } for u in users]
            
            logger.info(f"✅ Retrieved tenant: {tenant.company_name}")
            
            return jsonify({
                'success': True,
                'tenant': tenant_data,
                'users': users_data
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Get tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# Audit Log Routes
# ============================================================================

@admin_bp.route('/audit-logs', methods=['GET'])
@require_auth
def list_audit_logs():
    """
    List audit logs
    
    Query parameters:
    - admin_id: Filter by admin
    - action: Filter by action
    - entity_type: Filter by entity type
    - limit: Number of records (default 50)
    
    Response:
    {
        "success": true,
        "logs": [...]
    }
    """
    try:
        admin_info = request.admin_info
        session = get_db_session()
        
        try:
            # Get query parameters
            admin_id = request.args.get('admin_id', type=int)
            action = request.args.get('action')
            entity_type = request.args.get('entity_type')
            limit = request.args.get('limit', 50, type=int)
            
            # Build query
            query = session.query(AuditLog)
            
            if admin_id:
                query = query.filter_by(admin_id=admin_id)
            if action:
                query = query.filter_by(action=action)
            if entity_type:
                query = query.filter_by(entity_type=entity_type)
            
            logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            logs_data = []
            for log in logs:
                logs_data.append({
                    'id': log.id,
                    'admin': log.administrator.username if log.administrator else 'System',
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'changes': json.loads(log.changes) if log.changes else None,
                    'ip_address': log.ip_address,
                    'created_at': log.created_at.isoformat() if log.created_at else None
                })
            
            logger.info(f"✅ Retrieved {len(logs)} audit logs")
            
            return jsonify({
                'success': True,
                'count': len(logs_data),
                'logs': logs_data
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ List audit logs error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Admin routes module loaded successfully")
