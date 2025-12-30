
"""
Admin Routes API

Provides Flask endpoints for admin dashboard and management operations.

File location: pareto_agents/admin_routes.py
"""

import logging
from flask import Blueprint, request, jsonify

from .auth import require_auth
from .database import get_db_session, Tenant, User, Administrator, GoogleOauthCredentials

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
            tenant_count = session.query(Tenant).count()
            user_count = session.query(User).count()
            admin_count = session.query(Administrator).count()
            
            logger.info("✅ Dashboard data retrieved successfully")
            
            return jsonify({
                "success": True,
                "data": {
                    "statistics": {
                        "total_tenants": tenant_count,
                        "total_users": user_count,
                        "active_users": user_count, # Placeholder
                        "total_admins": admin_count,
                    }
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
    session = get_db_session()
    try:
        tenants = session.query(Tenant).all()
        return jsonify({"success": True, "data": [t.to_dict() for t in tenants]}), 200
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["GET"])
@require_auth
def get_tenant(tenant_id):
    session = get_db_session()
    try:
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404
        return jsonify({"success": True, "data": tenant.to_dict()}), 200
    finally:
        session.close()

@admin_bp.route("/tenants", methods=["POST"])
@require_auth
def create_tenant():
    data = request.get_json()
    session = get_db_session()
    try:
        new_tenant = Tenant(name=data["name"], is_active=data.get("is_active", True))
        session.add(new_tenant)
        session.commit()
        return jsonify({"success": True, "data": new_tenant.to_dict()}), 201
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["PUT"])
@require_auth
def update_tenant(tenant_id):
    data = request.get_json()
    session = get_db_session()
    try:
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404
        tenant.name = data.get("name", tenant.name)
        tenant.is_active = data.get("is_active", tenant.is_active)
        session.commit()
        return jsonify({"success": True, "data": tenant.to_dict()}), 200
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["DELETE"])
@require_auth
def delete_tenant(tenant_id):
    session = get_db_session()
    try:
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404
        session.delete(tenant)
        session.commit()
        return jsonify({"success": True, "message": "Tenant deleted"}), 200
    finally:
        session.close()


# ============================================================================
# User Management Endpoints
# ============================================================================


@admin_bp.route("/users", methods=["GET"])
@require_auth
def get_users():
    session = get_db_session()
    try:
        users = session.query(User).all()
        return jsonify({"success": True, "data": [u.to_dict() for u in users]}), 200
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id):
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        return jsonify({"success": True, "data": user.to_dict()}), 200
    finally:
        session.close()

@admin_bp.route("/users", methods=["POST"])
@require_auth
def create_user():
    data = request.get_json()
    session = get_db_session()
    try:
        new_user = User(
            tenant_id=data["tenant_id"],
            phone_number=data["phone_number"],
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            is_enabled=data.get("is_enabled", True)
        )
        session.add(new_user)
        session.commit()
        return jsonify({"success": True, "data": new_user.to_dict()}), 201
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth
def update_user(user_id):
    data = request.get_json()
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        user.tenant_id = data.get("tenant_id", user.tenant_id)
        user.phone_number = data.get("phone_number", user.phone_number)
        user.email = data.get("email", user.email)
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.is_enabled = data.get("is_enabled", user.is_enabled)
        session.commit()
        return jsonify({"success": True, "data": user.to_dict()}), 200
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user(user_id):
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        session.delete(user)
        session.commit()
        return jsonify({"success": True, "message": "User deleted"}), 200
    finally:
        session.close()


# ============================================================================
# Google OAuth Endpoints
# ============================================================================


@admin_bp.route("/tenants/<int:tenant_id>/google-oauth-credentials", methods=["POST"])
@require_auth
def save_google_oauth_credentials(tenant_id):
    data = request.get_json()
    session = get_db_session()
    try:
        creds = session.query(GoogleOauthCredentials).filter_by(tenant_id=tenant_id).first()
        if creds:
            creds.credentials_json = data["credentials_json"]
        else:
            creds = GoogleOauthCredentials(tenant_id=tenant_id, credentials_json=data["credentials_json"])
            session.add(creds)
        session.commit()
        return jsonify({"success": True, "message": "Google OAuth credentials saved"}), 200
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>/authorize-google", methods=["POST"])
@require_auth
def authorize_google(user_id):
    # Placeholder for Google OAuth flow
    return jsonify({"success": True, "message": "Google authorization flow initiated."}), 200
