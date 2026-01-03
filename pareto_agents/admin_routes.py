'''
Admin Management Routes

Provides Flask endpoints for:
- User management (CRUD)
- Tenant management (CRUD)
- Audit log viewing
- Admin dashboard

File location: pareto_agents/admin_routes.py
'''

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
    try:
        admin_info = request.admin_info
        session = get_db_session()
        try:
            tenant_count = session.query(Tenant).filter_by(is_active=True).count()
            user_count = session.query(User).count()
            active_user_count = session.query(User).filter_by(is_enabled=True).count()
            admin_count = session.query(Administrator).filter_by(is_active=True).count()
            
            recent_logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
            
            activity = [
                {
                    'id': log.id,
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'created_at': log.created_at.isoformat(),
                    'admin': log.administrator.username if log.administrator else 'System'
                } for log in recent_logs
            ]
            
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
        logger.error(f"Dashboard error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# User Management Routes
# ============================================================================

@admin_bp.route('/users', methods=['GET'])
@require_auth
def list_users():
    try:
        session = get_db_session()
        try:
            users = session.query(User).all()
            users_data = []
            for user in users:
                user_dict = user.to_dict()
                user_dict["has_token"] = bool(user.google_token_base64)
                users_data.append(user_dict)
            return jsonify({"success": True, "users": users_data}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"List users error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    try:
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            return jsonify({'success': True, 'user': user.to_dict()}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Get user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users', methods=['POST'])
@require_auth
def create_user():
    try:
        admin_info = request.admin_info
        data = request.get_json()
        if not data or not all(k in data for k in ['tenant_id', 'phone_number', 'first_name', 'last_name']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        session = get_db_session()
        try:
            user = User(
                tenant_id=data['tenant_id'],
                phone_number=data['phone_number'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data.get('email'),
                is_enabled=data.get('is_enabled', True)
            )
            session.add(user)
            session.commit()
            log_audit(admin_info['admin_id'], 'CREATE', 'USER', user.id, user.to_dict(), request.remote_addr)
            return jsonify({'success': True, 'user': user.to_dict()}), 201
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Create user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    try:
        admin_info = request.admin_info
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            changes = {}
            for key, value in data.items():
                if hasattr(user, key) and getattr(user, key) != value:
                    changes[key] = {'old': getattr(user, key), 'new': value}
                    setattr(user, key, value)
            
            if changes:
                user.updated_at = datetime.utcnow()
                session.commit()
                log_audit(admin_info['admin_id'], 'UPDATE', 'USER', user.id, changes, request.remote_addr)
            
            return jsonify({'success': True, 'user': user.to_dict()}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Update user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    try:
        admin_info = request.admin_info
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            log_audit(admin_info['admin_id'], 'DELETE', 'USER', user.id, user.to_dict(), request.remote_addr)
            session.delete(user)
            session.commit()
            return jsonify({'success': True}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Delete user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# Tenant Management Routes
# ============================================================================

@admin_bp.route('/tenants', methods=['GET'])
@require_auth
def list_tenants():
    try:
        session = get_db_session()
        try:
            tenants = session.query(Tenant).all()
            return jsonify({"success": True, "tenants": [tenant.to_dict(include_users=True) for tenant in tenants]}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"List tenants error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['GET'])
@require_auth
def get_tenant(tenant_id):
    try:
        session = get_db_session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return jsonify({'success': False, 'message': 'Tenant not found'}), 404
            return jsonify({"success": True, "tenant": tenant.to_dict(include_users=True)}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Get tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants', methods=['POST'])
@require_auth
def create_tenant():
    try:
        admin_info = request.admin_info
        data = request.get_json()
        if not data or not all(k in data for k in ['company_name', 'company_slug']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        session = get_db_session()
        try:
            tenant = Tenant(
                company_name=data['company_name'],
                company_slug=data['company_slug'],
                email=data.get('email'),
                phone=data.get('phone'),
                is_active=data.get('is_active', True),
                created_by_admin_id=admin_info['admin_id']
            )
            # Set 'name' field for backwards compatibility with old schema
            if hasattr(tenant, 'name') or True:  # Always try to set it
                try:
                    tenant.name = data['company_name']
                except AttributeError:
                    pass  # Column doesn't exist, ignore
            session.add(tenant)
            session.commit()
            log_audit(admin_info['admin_id'], 'CREATE', 'TENANT', tenant.id, tenant.to_dict(), request.remote_addr)
            return jsonify({'success': True, 'tenant': tenant.to_dict()}), 201
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Create tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['PUT'])
@require_auth
def update_tenant(tenant_id):
    try:
        admin_info = request.admin_info
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        session = get_db_session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return jsonify({'success': False, 'message': 'Tenant not found'}), 404
            
            changes = {}
            for key, value in data.items():
                if key == 'is_active':
                    if tenant.is_active != value:
                        changes[key] = {'old': tenant.is_active, 'new': value}
                        tenant.is_active = value
                elif hasattr(tenant, key) and getattr(tenant, key) != value:
                    changes[key] = {'old': getattr(tenant, key), 'new': value}
                    setattr(tenant, key, value)
            
            if changes:
                tenant.updated_at = datetime.utcnow()
                session.commit()
                log_audit(admin_info['admin_id'], 'UPDATE', 'TENANT', tenant.id, changes, request.remote_addr)
            
            return jsonify({'success': True, 'tenant': tenant.to_dict()}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Update tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['DELETE'])
@require_auth
def delete_tenant(tenant_id):
    try:
        admin_info = request.admin_info
        session = get_db_session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return jsonify({'success': False, 'message': 'Tenant not found'}), 404
            
            log_audit(admin_info['admin_id'], 'DELETE', 'TENANT', tenant.id, tenant.to_dict(), request.remote_addr)
            session.delete(tenant)
            session.commit()
            return jsonify({'success': True}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Delete tenant error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# Audit Log Routes
# ============================================================================

@admin_bp.route('/audit-logs', methods=['GET'])
@require_auth
def list_audit_logs():
    try:
        session = get_db_session()
        try:
            logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
            return jsonify({'success': True, 'logs': [log.to_dict() for log in logs]}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"List audit logs error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# ============================================================================
# Token Management Routes
# ============================================================================

@admin_bp.route("/users/<int:user_id>/token", methods=["GET"])
@require_auth
def get_user_token(user_id):
    """Get user's Google token data"""
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if not user.google_token_base64:
            return jsonify({"success": False, "message": "No token found for this user"}), 404
        
        try:
            import base64
            token_json = base64.b64decode(user.google_token_base64).decode('utf-8')
            token_data = json.loads(token_json)
            return jsonify({
                "success": True, 
                "token_data": token_data,
                "updated_at": user.google_token_updated_at.isoformat() if user.google_token_updated_at else None
            }), 200
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return jsonify({"success": False, "message": "Error reading token data"}), 500
    finally:
        session.close()


@admin_bp.route("/users/<int:user_id>/token", methods=["POST"])
@require_auth
def set_user_token(user_id):
    """Upload/update user's Google token"""
    admin_info = request.admin_info
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if "token_file" not in request.files:
            return jsonify({"success": False, "message": "No file provided"}), 400
        
        file = request.files["token_file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No selected file"}), 400
        
        try:
            import base64
            token_data = json.load(file)
            token_json = json.dumps(token_data)
            user.google_token_base64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
            user.google_token_updated_at = datetime.utcnow()
            session.commit()
            
            log_audit(admin_info['admin_id'], 'UPDATE', 'USER_TOKEN', user.id, 
                     {'action': 'token_uploaded'}, request.remote_addr)
            
            return jsonify({"success": True, "message": "Token uploaded successfully"}), 200
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "Invalid JSON file"}), 400
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return jsonify({"success": False, "message": "Error saving token"}), 500
    finally:
        session.close()


@admin_bp.route("/users/<int:user_id>/token", methods=["DELETE"])
@require_auth
def delete_user_token(user_id):
    """Delete user's Google token"""
    admin_info = request.admin_info
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if not user.google_token_base64:
            return jsonify({"success": False, "message": "No token to delete"}), 404
        
        user.google_token_base64 = None
        user.google_token_updated_at = None
        session.commit()
        
        log_audit(admin_info['admin_id'], 'DELETE', 'USER_TOKEN', user.id, 
                 {'action': 'token_deleted'}, request.remote_addr)
        
        return jsonify({"success": True, "message": "Token deleted successfully"}), 200
    finally:
        session.close()
