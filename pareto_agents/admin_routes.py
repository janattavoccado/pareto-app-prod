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
                users_data.append(user.to_dict())
            
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
            
            logger.info(f"✅ Retrieved user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
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
        "enabled": true
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
                is_enabled=data.get('enabled', True)
            )
            
            session.add(user)
            session.commit()
            
            # Log audit
            log_audit(
                admin_id=admin_info['admin_id'],
                action='CREATE',
                entity_type='USER',
                entity_id=user.id,
                changes=user.to_dict(),
                ip_address=request.remote_addr
            )
            
            logger.info(f"✅ User created: {user.full_name}")
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
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
    Update user details
    
    Request body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "enabled": true
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
            if 'first_name' in data and data['first_name'] != user.first_name:
                changes['first_name'] = {'old': user.first_name, 'new': data['first_name']}
                user.first_name = data['first_name']
            
            if 'last_name' in data and data['last_name'] != user.last_name:
                changes['last_name'] = {'old': user.last_name, 'new': data['last_name']}
                user.last_name = data['last_name']
            
            if 'email' in data and data['email'] != user.email:
                changes['email'] = {'old': user.email, 'new': data['email']}
                user.email = data['email']
            
            if 'is_enabled' in data and data['is_enabled'] != user.is_enabled:
                changes['is_enabled'] = {'old': user.is_enabled, 'new': data['is_enabled']}
                user.is_enabled = data['is_enabled']
            
            if changes:
                user.updated_at = datetime.utcnow()
                session.commit()
                
                # Log audit
                log_audit(
                    admin_id=admin_info['admin_id'],
                    action='UPDATE',
                    entity_type='USER',
                    entity_id=user.id,
                    changes=changes,
                    ip_address=request.remote_addr
                )
                
                logger.info(f"✅ User updated: {user.full_name}")
            
            return jsonify({
                'success': True,
                'user': user.to_dict()
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
        "success": true
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
            
            # Log audit before deleting
            log_audit(
                admin_id=admin_info['admin_id'],
                action='DELETE',
                entity_type='USER',
                entity_id=user.id,
                changes=user.to_dict(),
                ip_address=request.remote_addr
            )
            
            session.delete(user)
            session.commit()
            
            logger.info(f"✅ User deleted: {user.full_name}")
            
            return jsonify({'success': True}), 200
        
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
def get_tenants():
    """
    Get all tenants
    
    Response:
    {
        "success": true,
        "data": [...]
    }
    """
    session = get_db_session()
    try:
        tenants = session.query(Tenant).all()
        return jsonify({'success': True, 'data': [t.to_dict() for t in tenants]}), 200
    finally:
        session.close()


@admin_bp.route('/tenants', methods=['POST'])
@require_auth
def create_tenant():
    """
    Create a new tenant
    
    Request body:
    {
        "company_name": "New Company",
        "company_slug": "new-company",
        "email": "contact@new-company.com",
        "phone": "123-456-7890"
    }
    
    Response:
    {
        "success": true,
        "tenant": {...}
    }
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['company_name', 'company_slug']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        session = get_db_session()
        
        try:
            # Check for duplicate name or slug
            if session.query(Tenant).filter_by(company_name=data['company_name']).first():
                return jsonify({'success': False, 'message': 'Company name already exists'}), 409
            if session.query(Tenant).filter_by(company_slug=data['company_slug']).first():
                return jsonify({'success': False, 'message': 'Company slug already exists'}), 409

            tenant = Tenant(
                company_name=data['company_name'],
                company_slug=data['company_slug'],
                email=data.get('email'),
                phone=data.get('phone'),
                created_by_admin_id=admin_info['admin_id']
            )
            
            session.add(tenant)
            session.commit()
            
            # Log audit
            log_audit(
                admin_id=admin_info['admin_id'],
                action='CREATE',
                entity_type='TENANT',
                entity_id=tenant.id,
                changes=tenant.to_dict(),
                ip_address=request.remote_addr
            )
            
            logger.info(f"✅ Tenant created: {tenant.company_name}")
            
            return jsonify({
                'success': True,
                'tenant': tenant.to_dict()
            }), 201
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Create tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['PUT'])
@require_auth
def update_tenant(tenant_id):
    """
    Update tenant details
    
    Request body:
    {
        "company_name": "Updated Company",
        "email": "updated@company.com",
        "phone": "987-654-3210",
        "is_active": false
    }
    
    Response:
    {
        "success": true,
        "tenant": {...}
    }
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        session = get_db_session()
        
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            
            if not tenant:
                logger.warning(f"❌ Tenant not found: {tenant_id}")
                return jsonify({'success': False, 'message': 'Tenant not found'}), 404
            
            # Track changes
            changes = {}
            
            # Update fields
            if 'company_name' in data and data['company_name'] != tenant.company_name:
                # Check for duplicate name
                if session.query(Tenant).filter(Tenant.id != tenant_id, Tenant.company_name == data['company_name']).first():
                    return jsonify({'success': False, 'message': 'Company name already exists'}), 409
                changes['company_name'] = {'old': tenant.company_name, 'new': data['company_name']}
                tenant.company_name = data['company_name']
            
            if 'email' in data and data['email'] != tenant.email:
                changes['email'] = {'old': tenant.email, 'new': data['email']}
                tenant.email = data['email']
            
            if 'phone' in data and data['phone'] != tenant.phone:
                changes['phone'] = {'old': tenant.phone, 'new': data['phone']}
                tenant.phone = data['phone']
            
            if 'is_active' in data and data['is_active'] != tenant.is_active:
                changes['is_active'] = {'old': tenant.is_active, 'new': data['is_active']}
                tenant.is_active = data['is_active']
            
            if changes:
                tenant.updated_at = datetime.utcnow()
                session.commit()
                
                # Log audit
                log_audit(
                    admin_id=admin_info['admin_id'],
                    action='UPDATE',
                    entity_type='TENANT',
                    entity_id=tenant.id,
                    changes=changes,
                    ip_address=request.remote_addr
                )
                
                logger.info(f"✅ Tenant updated: {tenant.company_name}")
            
            return jsonify({
                'success': True,
                'tenant': tenant.to_dict()
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Update tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['DELETE'])
@require_auth
def delete_tenant(tenant_id):
    """
    Delete a tenant
    
    Response:
    {
        "success": true
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
            
            # Log audit before deleting
            log_audit(
                admin_id=admin_info['admin_id'],
                action='DELETE',
                entity_type='TENANT',
                entity_id=tenant.id,
                changes=tenant.to_dict(),
                ip_address=request.remote_addr
            )
            
            session.delete(tenant)
            session.commit()
            
            logger.info(f"✅ Tenant deleted: {tenant.company_name}")
            
            return jsonify({'success': True}), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Delete tenant error: {e}", exc_info=True)
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
    - admin_id: Filter by admin ID
    - entity_type: Filter by entity type (USER, TENANT, etc.)
    - entity_id: Filter by entity ID
    
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
            entity_type = request.args.get('entity_type')
            entity_id = request.args.get('entity_id', type=int)
            
            # Build query
            query = session.query(AuditLog)
            
            if admin_id:
                query = query.filter_by(admin_id=admin_id)
            
            if entity_type:
                query = query.filter_by(entity_type=entity_type)
            
            if entity_id:
                query = query.filter_by(entity_id=entity_id)
            
            logs = query.order_by(AuditLog.created_at.desc()).all()
            
            logs_data = []
            for log in logs:
                logs_data.append({
                    'id': log.id,
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'changes': json.loads(log.changes) if log.changes else None,
                    'ip_address': log.ip_address,
                    'created_at': log.created_at.isoformat(),
                    'admin': log.administrator.username if log.administrator else 'System'
                })
            
            logger.info(f"✅ Listed {len(logs)} audit logs")
            
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
```
