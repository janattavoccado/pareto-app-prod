"""
Admin Routes API

Provides Flask endpoints for admin dashboard and management operations.

File location: pareto_agents/admin_routes.py
"""

import logging
from flask import Blueprint, request, jsonify

from .auth import require_auth
from .database import get_db_session, Tenant, User, Administrator

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ============================================================================
# Dashboard Endpoint
# ============================================================================


@admin_bp.route("/dashboard", methods=["GET"])
@require_auth
def dashboard():
    """
    Admin dashboard endpoint - returns statistics and data
    """
    try:
        session = get_db_session()
        
        try:
            # Get tenant count - handle missing columns gracefully
            try:
                tenant_count = session.query(Tenant).filter_by(is_active=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting tenant count: {e}")
                tenant_count = 0
            
            # Get user count - handle missing columns gracefully
            try:
                user_count = session.query(User).filter_by(is_enabled=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting user count: {e}")
                user_count = 0
            
            # Get admin count
            try:
                admin_count = session.query(Administrator).filter_by(is_active=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting admin count: {e}")
                admin_count = 0
            
            # Get recent tenants
            try:
                recent_tenants = session.query(Tenant).filter_by(is_active=True).limit(5).all()
                tenants_data = [
                    {
                        "id": t.id,
                        "name": t.name,
                        "is_active": t.is_active,
                        "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') and t.created_at else None,
                        "updated_at": t.updated_at.isoformat() if hasattr(t, 'updated_at') and t.updated_at else None,
                    }
                    for t in recent_tenants
                ]
            except Exception as e:
                logger.warning(f"⚠️  Error getting recent tenants: {e}")
                tenants_data = []
            
            # Get recent users
            try:
                recent_users = session.query(User).filter_by(is_enabled=True).limit(5).all()
                users_data = [
                    {
                        "id": u.id,
                        "phone_number": u.phone_number,
                        "email": u.email,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "is_enabled": u.is_enabled,
                        "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else None,
                    }
                    for u in recent_users
                ]
            except Exception as e:
                logger.warning(f"⚠️  Error getting recent users: {e}")
                users_data = []
            
            logger.info("✅ Dashboard data retrieved successfully")
            
            return jsonify({
                "success": True,
                "data": {
                    "statistics": {
                        "tenant_count": tenant_count,
                        "user_count": user_count,
                        "admin_count": admin_count,
                    },
                    "recent_tenants": tenants_data,
                    "recent_users": users_data,
                }
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while loading the dashboard",
            "error": str(e)
        }), 500


# ============================================================================
# Tenant Management Endpoints
# ============================================================================


@admin_bp.route("/tenants", methods=["GET"])
@require_auth
def get_tenants():
    """
    Get all tenants
    """
    try:
        session = get_db_session()
        
        try:
            tenants = session.query(Tenant).all()
            tenants_data = [
                {
                    "id": t.id,
                    "name": t.name,
                    "is_active": t.is_active,
                    "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') and t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if hasattr(t, 'updated_at') and t.updated_at else None,
                }
                for t in tenants
            ]
            
            logger.info(f"✅ Retrieved {len(tenants_data)} tenants")
            return jsonify({
                "success": True,
                "data": tenants_data
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting tenants: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while retrieving tenants"
        }), 500


@admin_bp.route("/tenants/<int:tenant_id>", methods=["GET"])
@require_auth
def get_tenant(tenant_id):
    """
    Get a specific tenant
    """
    try:
        session = get_db_session()
        
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            
            if not tenant:
                return jsonify({
                    "success": False,
                    "message": "Tenant not found"
                }), 404
            
            tenant_data = {
                "id": tenant.id,
                "name": tenant.name,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat() if hasattr(tenant, 'created_at') and tenant.created_at else None,
                "updated_at": tenant.updated_at.isoformat() if hasattr(tenant, 'updated_at') and tenant.updated_at else None,
            }
            
            logger.info(f"✅ Retrieved tenant {tenant_id}")
            return jsonify({
                "success": True,
                "data": tenant_data
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting tenant: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while retrieving the tenant"
        }), 500


# ============================================================================
# User Management Endpoints
# ============================================================================


@admin_bp.route("/users", methods=["GET"])
@require_auth
def get_users():
    """
    Get all users
    """
    try:
        session = get_db_session()
        
        try:
            users = session.query(User).all()
            users_data = [
                {
                    "id": u.id,
                    "phone_number": u.phone_number,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "is_enabled": u.is_enabled,
                    "created_at": u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else None,
                }
                for u in users
            ]
            
            logger.info(f"✅ Retrieved {len(users_data)} users")
            return jsonify({
                "success": True,
                "data": users_data
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting users: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while retrieving users"
        }), 500


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id):
    """
    Get a specific user
    """
    try:
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404
            
            user_data = {
                "id": user.id,
                "phone_number": user.phone_number,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_enabled": user.is_enabled,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
            }
            
            logger.info(f"✅ Retrieved user {user_id}")
            return jsonify({
                "success": True,
                "data": user_data
            }), 200
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting user: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An error occurred while retrieving the user"
        }), 500


# ============================================================================
# Health Check Route
# ============================================================================


@admin_bp.route("/health", methods=["GET"])
def admin_health():
    """
    Health check endpoint for admin API
    """
    return jsonify({"status": "healthy", "service": "Admin API"}), 200


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info("Admin routes module loaded successfully")
