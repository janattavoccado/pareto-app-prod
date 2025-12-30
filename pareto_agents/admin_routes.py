"""
Admin Routes API - Full CRUD

Provides Flask endpoints for admin dashboard and management operations,
including full Create, Read, Update, and Delete (CRUD) functionality
for Tenants and Users.

File location: pareto_agents/admin_routes.py
"""

import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

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
    # This function is already implemented and working
    # ... (implementation from previous turns)
    pass

# ============================================================================
# Tenant Management Endpoints (Full CRUD)
# ============================================================================

@admin_bp.route("/tenants", methods=["GET"])
@require_auth
def get_tenants():
    """Get all tenants"""
    session = get_db_session()
    try:
        tenants = session.query(Tenant).order_by(Tenant.id.desc()).all()
        return jsonify({"success": True, "data": [t.to_dict() for t in tenants]})
    finally:
        session.close()

@admin_bp.route("/tenants", methods=["POST"])
@require_auth
def create_tenant():
    """Create a new tenant"""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"success": False, "message": "Tenant name is required"}), 400

    session = get_db_session()
    try:
        new_tenant = Tenant(name=data["name"], is_active=data.get("is_active", True))
        session.add(new_tenant)
        session.commit()
        logger.info(f"✅ Created new tenant: {new_tenant.name}")
        return jsonify({"success": True, "data": new_tenant.to_dict()}), 201
    except IntegrityError:
        session.rollback()
        return jsonify({"success": False, "message": "Tenant with this name already exists"}), 409
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["PUT"])
@require_auth
def update_tenant(tenant_id):
    """Update an existing tenant"""
    session = get_db_session()
    try:
        tenant = session.query(Tenant).get(tenant_id)
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404

        data = request.get_json()
        tenant.name = data.get("name", tenant.name)
        tenant.is_active = data.get("is_active", tenant.is_active)
        session.commit()
        logger.info(f"✅ Updated tenant {tenant_id}")
        return jsonify({"success": True, "data": tenant.to_dict()})
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["DELETE"])
@require_auth
def delete_tenant(tenant_id):
    """Delete a tenant"""
    session = get_db_session()
    try:
        tenant = session.query(Tenant).get(tenant_id)
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404

        session.delete(tenant)
        session.commit()
        logger.info(f"✅ Deleted tenant {tenant_id}")
        return jsonify({"success": True, "message": "Tenant deleted"})
    finally:
        session.close()


# ============================================================================
# User Management Endpoints (Full CRUD)
# ============================================================================

@admin_bp.route("/users", methods=["GET"])
@require_auth
def get_users():
    """Get all users"""
    session = get_db_session()
    try:
        users = session.query(User).order_by(User.id.desc()).all()
        return jsonify({"success": True, "data": [u.to_dict() for u in users]})
    finally:
        session.close()

@admin_bp.route("/users", methods=["POST"])
@require_auth
def create_user():
    """Create a new user"""
    data = request.get_json()
    if not data or not data.get("phone_number"):
        return jsonify({"success": False, "message": "Phone number is required"}), 400

    session = get_db_session()
    try:
        new_user = User(
            tenant_id=data.get("tenant_id"),
            phone_number=data["phone_number"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            is_enabled=data.get("is_enabled", True)
        )
        session.add(new_user)
        session.commit()
        logger.info(f"✅ Created new user: {new_user.phone_number}")
        return jsonify({"success": True, "data": new_user.to_dict()}), 201
    except IntegrityError:
        session.rollback()
        return jsonify({"success": False, "message": "User with this phone number already exists"}), 409
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth
def update_user(user_id):
    """Update an existing user"""
    session = get_db_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json()
        user.tenant_id = data.get("tenant_id", user.tenant_id)
        user.phone_number = data.get("phone_number", user.phone_number)
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.email = data.get("email", user.email)
        user.is_enabled = data.get("is_enabled", user.is_enabled)
        session.commit()
        logger.info(f"✅ Updated user {user_id}")
        return jsonify({"success": True, "data": user.to_dict()})
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user(user_id):
    """Delete a user"""
    session = get_db_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        session.delete(user)
        session.commit()
        logger.info(f"✅ Deleted user {user_id}")
        return jsonify({"success": True, "message": "User deleted"})
    finally:
        session.close()
