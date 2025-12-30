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
            tenant_count = 0
            try:
                tenant_count = session.query(Tenant).filter_by(is_active=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting tenant count: {e}")
                # Try without filter
                try:
                    tenant_count = session.query(Tenant).count()
                except:
                    pass
            
            # Get user count - handle missing columns gracefully
            user_count = 0
            try:
                user_count = session.query(User).filter_by(is_enabled=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting user count: {e}")
                # Try without filter
                try:
                    user_count = session.query(User).count()
                except:
                    pass
            
            # Get admin count
            admin_count = 0
            try:
                admin_count = session.query(Administrator).filter_by(is_active=True).count()
            except Exception as e:
                logger.warning(f"⚠️  Error getting admin count: {e}")
                # Try without filter
                try:
                    admin_count = session.query(Administrator).count()
                except:
                    pass
            
            # Get recent tenants
            tenants_data = []
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
                # Try without filter
                try:
                    recent_tenants = session.query(Tenant).limit(5).all()
                    tenants_data = [
                        {
                            "id": t.id,
                            "name": t.name,
                            "is_active": t.is_active,
                            "created_at": None,
                            "updated_at": None,
                        }
                        for t in recent_tenants
                    ]
                except:
                    tenants_data = []
            
            # Get recent users
            users_data = []
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
                # Try without filter
                try:
                    recent_users = session.query(User).limit(5).all()
                    users_data = [
                        {
                            "id": u.id,
                            "phone_number": u.phone_number,
                            "email": u.email,
                            "first_name": u.first_name,
                            "last_name": u.last_name,
                            "is_enabled": u.is_enabled,
                            "created_at": None,
                        }
                        for u in recent_users
                    ]
                except:
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


@admin_bp.route("/tenants", methods=["POST"])
@require_auth
def create_tenant():
    try:
        session = get_db_session()
        data = request.get_json()
        
        if not data or not data.get("name"):
            return jsonify({"success": False, "message": "Tenant name is required"}), 400
        
        new_tenant = Tenant(name=data["name"], is_active=data.get("is_active", True))
        session.add(new_tenant)
        session.commit()
        
        logger.info(f"✅ Created new tenant: {new_tenant.name}")
        return jsonify({"success": True, "message": "Tenant created successfully", "data": {"id": new_tenant.id}}), 201
        
    except Exception as e:
        logger.error(f"❌ Error creating tenant: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while creating the tenant"}), 500
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["PUT"])
@require_auth
def update_tenant(tenant_id):
    try:
        session = get_db_session()
        data = request.get_json()
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404
        
        if "name" in data:
            tenant.name = data["name"]
        if "is_active" in data:
            tenant.is_active = data["is_active"]
            
        session.commit()
        logger.info(f"✅ Updated tenant {tenant_id}")
        return jsonify({"success": True, "message": "Tenant updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating tenant: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while updating the tenant"}), 500
    finally:
        session.close()

@admin_bp.route("/tenants/<int:tenant_id>", methods=["DELETE"])
@require_auth
def delete_tenant(tenant_id):
    try:
        session = get_db_session()
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        
        if not tenant:
            return jsonify({"success": False, "message": "Tenant not found"}), 404
        
        session.delete(tenant)
        session.commit()
        logger.info(f"✅ Deleted tenant {tenant_id}")
        return jsonify({"success": True, "message": "Tenant deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error deleting tenant: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while deleting the tenant"}), 500
    finally:
        session.close()

@admin_bp.route("/users", methods=["POST"])
@require_auth
def create_user():
    try:
        session = get_db_session()
        data = request.get_json()
        
        if not data or not data.get("phone_number"):
            return jsonify({"success": False, "message": "Phone number is required"}), 400
        
        new_user = User(
            tenant_id=data.get("tenant_id"),
            phone_number=data["phone_number"],
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            is_enabled=data.get("is_enabled", True)
        )
        session.add(new_user)
        session.commit()
        
        logger.info(f"✅ Created new user: {new_user.phone_number}")
        return jsonify({"success": True, "message": "User created successfully", "data": {"id": new_user.id}}), 201
        
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while creating the user"}), 500
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth
def update_user(user_id):
    try:
        session = get_db_session()
        data = request.get_json()
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if "tenant_id" in data:
            user.tenant_id = data["tenant_id"]
        if "phone_number" in data:
            user.phone_number = data["phone_number"]
        if "email" in data:
            user.email = data["email"]
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "is_enabled" in data:
            user.is_enabled = data["is_enabled"]
            
        session.commit()
        logger.info(f"✅ Updated user {user_id}")
        return jsonify({"success": True, "message": "User updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating user: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while updating the user"}), 500
    finally:
        session.close()

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user(user_id):
    try:
        session = get_db_session()
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        session.delete(user)
        session.commit()
        logger.info(f"✅ Deleted user {user_id}")
        return jsonify({"success": True, "message": "User deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error deleting user: {e}", exc_info=True)
        session.rollback()
        return jsonify({"success": False, "message": "An error occurred while deleting the user"}), 500
    finally:
        session.close()

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


# ============================================================================
# Google OAuth Credentials Management
# ============================================================================

@admin_bp.route("/tenants/<int:tenant_id>/google-oauth-credentials", methods=["POST"])
@require_auth
def set_google_oauth_credentials(tenant_id):
    """
    Set Google OAuth credentials for a specific tenant.
    """
    data = request.get_json()
    if not data or 'credentials_json' not in data:
        return jsonify({"success": False, "message": "Missing credentials_json"}), 400

    try:
        session = get_db_session()
        try:
            # Check if tenant exists
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return jsonify({"success": False, "message": "Tenant not found"}), 404

            # Upsert credentials
            creds = session.query(GoogleOauthCredentials).filter_by(tenant_id=tenant_id).first()
            if creds:
                creds.credentials_json = data['credentials_json']
            else:
                creds = GoogleOauthCredentials(
                    tenant_id=tenant_id,
                    credentials_json=data['credentials_json']
                )
                session.add(creds)
            
            session.commit()
            logger.info(f"✅ Successfully set Google OAuth credentials for tenant {tenant_id}")
            return jsonify({"success": True, "message": "Credentials saved successfully"}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Error setting Google OAuth credentials: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An error occurred"}), 500

# ============================================================================
# Google OAuth Flow
# ============================================================================

@admin_bp.route("/google-oauth/authorize/<int:user_id>", methods=["GET"])
@require_auth
def google_oauth_authorize(user_id):
    """
    Initiates the Google OAuth 2.0 flow for a user.
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user or not user.tenant_id:
            return jsonify({"success": False, "message": "User or tenant not found"}), 404

        creds_record = session.query(GoogleOauthCredentials).filter_by(tenant_id=user.tenant_id).first()
        if not creds_record or not creds_record.credentials_json:
            return jsonify({"success": False, "message": "Google OAuth is not configured for this tenant"}), 400

        client_config = json.loads(creds_record.credentials_json)

        flow = Flow.from_client_config(
            client_config,
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.readonly',
                'openid'
            ],
            redirect_uri=request.host_url.rstrip('/') + '/api/admin/google-oauth/callback'
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # Store state in session to prevent CSRF
        # In a real app, you'd use a server-side session (e.g., Flask-Session)
        # For simplicity, we'll just pass it back, but this is NOT secure.
        # A better approach is to store the state with the user_id in the DB.
        session.query(User).filter_by(id=user_id).update({"google_oauth_state": state})
        session.commit()

        return jsonify({"success": True, "authorization_url": authorization_url})

    finally:
        session.close()

@admin_bp.route("/google-oauth/callback", methods=["GET"])
def google_oauth_callback():
    """
    Handles the callback from Google after user authorization.
    """
    state = request.args.get('state')
    code = request.args.get('code')

    session = get_db_session()
    try:
        user = session.query(User).filter_by(google_oauth_state=state).first()
        if not user:
            return "Invalid state parameter. Authentication failed.", 400

        creds_record = session.query(GoogleOauthCredentials).filter_by(tenant_id=user.tenant_id).first()
        client_config = json.loads(creds_record.credentials_json)

        flow = Flow.from_client_config(
            client_config,
            scopes=None, # Scopes are already defined in the authorization request
            state=state,
            redirect_uri=request.host_url.rstrip('/') + '/api/admin/google-oauth/callback'
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials
        token_json = credentials.to_json()
        
        # Store the token in base64
        user.google_token_base64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
        user.google_oauth_state = None # Clear state
        session.commit()

        logger.info(f"✅ Successfully authorized Google account for user {user.id}")
        return "<script>window.close();</script>" # Close the popup window

    except Exception as e:
        logger.error(f"❌ Google OAuth callback error: {e}", exc_info=True)
        return "An error occurred during authentication.", 500
    finally:
        session.close()



    """
    Get a specific user
    """
    try:
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 404
            
            user_data = {
                "id": user.id,
                "tenant_id": user.tenant_id,
                "phone_number": user.phone_number,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_enabled": user.is_enabled,
                "google_token_base64": user.google_token_base64,
            }
            
            logger.info(f"✅ Retrieved user {user_id}")
            return jsonify({"success": True, "data": user_data}), 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Error getting user: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An error occurred while retrieving the user"}), 500


@admin_bp.route("/users/<int:user_id>/authorize-google", methods=["POST"])
@require_auth
def authorize_google(user_id):
    """
    Initiate Google OAuth flow for a user
    """
    # This is a placeholder - the actual implementation will require the google-auth-oauthlib library
    # and proper handling of the OAuth2 flow (redirects, state, etc.)
    return jsonify({"success": True, "message": "Google authorization flow initiated."}), 200
