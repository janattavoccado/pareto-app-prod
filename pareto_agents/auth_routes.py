'''
Authentication API Routes

Provides Flask endpoints for:
- Admin login
- Admin logout
- Session validation
- Password change

File location: pareto_agents/auth_routes.py
'''

import logging
from flask import Blueprint, request, jsonify, make_response

from .auth import AuthenticationService, SessionManager, PasswordManager, require_auth
from .database import get_db_session, Administrator

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ============================================================================
# Authentication Routes
# ============================================================================


@auth_bp.route("/login", methods=['POST'])
def login():
    """
    Administrator login endpoint
    """
    try:
        data = request.get_json()

        if not data:
            logger.warning("❌ Login: empty request body")
            return (
                jsonify({"success": False, "message": "Request body is required"}),
                400,
            )

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            logger.warning("❌ Login: missing username or password")
            return (
                jsonify(
                    {"success": False, "message": "Username and password are required"}
                ),
                400,
            )

        # Get client info
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")

        # Attempt login
        success, session_token, message = AuthenticationService.login(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            logger.warning(f"❌ Login failed for {username}: {message}")
            return jsonify({"success": False, "message": message}), 401

        # Get admin info
        session = get_db_session()
        try:
            admin = session.query(Administrator).filter_by(username=username).first()
            admin_info = {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email or "",
                "full_name": admin.full_name or "",
            }
        finally:
            session.close()

        # Create response
        response = make_response(
            jsonify(
                {
                    "success": True,
                    "message": message,
                    "session_token": session_token,
                    "admin": admin_info,
                }
            ),
            200,
        )

        # Set session cookie (optional, for browser-based access)
        response.set_cookie(
            "session_token",
            session_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=86400,  # 24 hours
        )

        logger.info(f"✅ Login successful for {username}")
        return response

    except Exception as e:
        logger.error(f"❌ Login error: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "An error occurred during login"}),
            500,
        )


@auth_bp.route("/logout", methods=['POST'])
@require_auth
def logout():
    """
    Administrator logout endpoint
    """
    try:
        session_token = request.session_token

        success, message = AuthenticationService.logout(session_token)

        if success:
            logger.info("✅ Logout successful")
            return jsonify({"success": True, "message": message}), 200
        else:
            logger.warning(f"❌ Logout failed: {message}")
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        logger.error(f"❌ Logout error: {e}", exc_info=True)
        return (
            jsonify({"success": False, "message": "An error occurred during logout"}),
            500,
        )


@auth_bp.route("/validate", methods=['GET'])
@require_auth
def validate_session():
    """
    Validate current session
    """
    try:
        admin_info = request.admin_info
        
        # Ensure admin_id is included for compatibility with other routes
        if "admin_id" not in admin_info and "id" in admin_info:
            admin_info["admin_id"] = admin_info["id"]

        logger.info(f"✅ Session validated for {admin_info.get('username')}")
        return jsonify({"success": True, "admin": admin_info}), 200

    except Exception as e:
        logger.error(f"❌ Session validation error: {e}", exc_info=True)
        return (
            jsonify(
                {"success": False, "message": "An error occurred during validation"}
            ),
            500,
        )


@auth_bp.route("/change-password", methods=['POST'])
@require_auth
def change_password():
    """
    Change administrator password
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()

        if not data:
            logger.warning("❌ Change password: empty request body")
            return (
                jsonify({"success": False, "message": "Request body is required"}),
                400,
            )

        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        if not old_password or not new_password:
            logger.warning("❌ Change password: missing passwords")
            return (
                jsonify(
                    {"success": False, "message": "Old and new passwords are required"}
                ),
                400,
            )

        # Change password
        # Use .get() to safely access admin_id or id
        admin_id = admin_info.get("admin_id") or admin_info.get("id")
        if not admin_id:
            return jsonify({"success": False, "message": "Admin ID not found in session"}), 400

        success, message = AuthenticationService.change_password(
            admin_id=admin_id,
            old_password=old_password,
            new_password=new_password,
        )

        if success:
            logger.info(f"✅ Password changed for {admin_info.get('username')}")
            return jsonify({"success": True, "message": message}), 200
        else:
            logger.warning(f"❌ Password change failed: {message}")
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        logger.error(f"❌ Change password error: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An error occurred"}), 500


# ============================================================================
# Health Check Routes
# ============================================================================


@auth_bp.route("/health", methods=['GET'])
def auth_health():
    """
    Health check endpoint for authentication service
    """
    return (
        jsonify({"status": "healthy", "service": "Authentication API"}),
        200,
    )


if __name__ == "__main__":
    # Test script
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("Authentication routes module loaded successfully")
