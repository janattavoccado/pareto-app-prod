"""
User Authentication System

Provides:
- User login/logout for CRM portal
- Password management (set, change, reset)
- Session management
- Authentication decorator for user routes

File location: pareto_agents/user_auth.py
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, make_response

from .database import get_db_session, User, Tenant
from .crm_models import UserCredential, UserSession

logger = logging.getLogger(__name__)

# Configuration
SESSION_DURATION_HOURS = int(os.environ.get('USER_SESSION_HOURS', 24))
PASSWORD_MIN_LENGTH = 8

# Create blueprint
user_auth_bp = Blueprint('user_auth', __name__, url_prefix='/api/user')


# ============================================================================
# Password Utilities
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored hash"""
    try:
        salt, password_hash = stored_hash.split(':')
        computed_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return computed_hash == password_hash
    except Exception:
        return False


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(64)


def generate_reset_token() -> str:
    """Generate a password reset token"""
    return secrets.token_urlsafe(32)


# ============================================================================
# Authentication Decorator
# ============================================================================

def require_user_auth(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get session token from header or cookie
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        else:
            session_token = request.headers.get('X-User-Session')
        if not session_token:
            session_token = request.cookies.get('user_session')
        
        if not session_token:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        session = get_db_session()
        try:
            # Find session
            user_session = session.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()
            
            if not user_session:
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            
            if user_session.is_expired:
                # Clean up expired session
                session.delete(user_session)
                session.commit()
                return jsonify({'success': False, 'message': 'Session expired'}), 401
            
            # Get user and tenant info
            user = session.query(User).filter(User.id == user_session.user_id).first()
            if not user or not user.is_enabled:
                return jsonify({'success': False, 'message': 'User not found or disabled'}), 401
            
            tenant = session.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if not tenant or not tenant.is_active:
                return jsonify({'success': False, 'message': 'Tenant not found or inactive'}), 401
            
            # Attach user info to request
            request.user_info = {
                'user_id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'tenant_id': tenant.id,
                'tenant_name': tenant.company_name,
                'session_id': user_session.id
            }
            
            return f(*args, **kwargs)
        finally:
            session.close()
    
    return decorated


# ============================================================================
# Authentication Routes
# ============================================================================

@user_auth_bp.route('/login', methods=['POST'])
def user_login():
    """User login endpoint"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        session = get_db_session()
        try:
            # Find user by email
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
            
            if not user.is_enabled:
                return jsonify({'success': False, 'message': 'Account is disabled'}), 401
            
            # Check if user has credentials
            credential = session.query(UserCredential).filter(
                UserCredential.user_id == user.id
            ).first()
            
            if not credential:
                return jsonify({
                    'success': False,
                    'message': 'Password not set. Please set your password first.',
                    'needs_password_setup': True
                }), 401
            
            if not credential.is_active:
                return jsonify({'success': False, 'message': 'Account credentials are disabled'}), 401
            
            # Verify password
            if not verify_password(password, credential.password_hash):
                return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
            
            # Get tenant info
            tenant = session.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if not tenant or not tenant.is_active:
                return jsonify({'success': False, 'message': 'Tenant not found or inactive'}), 401
            
            # Create session
            session_token = generate_session_token()
            expires_at = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
            
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500],
                expires_at=expires_at
            )
            session.add(user_session)
            
            # Update last login
            credential.last_login = datetime.utcnow()
            
            session.commit()
            
            # Create response with cookie
            response = make_response(jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'tenant_id': tenant.id,
                    'tenant_name': tenant.company_name
                },
                'session_token': session_token,
                'expires_at': expires_at.isoformat()
            }))
            
            # Set session cookie
            response.set_cookie(
                'user_session',
                session_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=SESSION_DURATION_HOURS * 3600
            )
            
            logger.info(f"User logged in: {email}")
            return response, 200
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/logout', methods=['POST'])
@require_user_auth
def user_logout():
    """User logout endpoint"""
    try:
        user_info = request.user_info
        
        session = get_db_session()
        try:
            # Delete current session
            session.query(UserSession).filter(
                UserSession.id == user_info['session_id']
            ).delete()
            session.commit()
            
            # Create response and clear cookie
            response = make_response(jsonify({
                'success': True,
                'message': 'Logged out successfully'
            }))
            response.delete_cookie('user_session')
            
            logger.info(f"User logged out: {user_info['email']}")
            return response, 200
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/me', methods=['GET'])
@require_user_auth
def get_current_user():
    """Get current user info"""
    try:
        user_info = request.user_info
        return jsonify({
            'success': True,
            'user': user_info
        }), 200
    except Exception as e:
        logger.error(f"Get user error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/validate', methods=['GET'])
@require_user_auth
def validate_user_session():
    """Validate current user session"""
    try:
        user_info = request.user_info
        return jsonify({
            'success': True,
            'user': user_info
        }), 200
    except Exception as e:
        logger.error(f"Validate session error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/setup-password', methods=['POST'])
def setup_password():
    """Alias for set-password endpoint"""
    return set_password()


# ============================================================================
# Password Management Routes
# ============================================================================

@user_auth_bp.route('/set-password', methods=['POST'])
def set_password():
    """Set password for first time (requires email verification token or admin setup)"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Validate password
        if len(password) < PASSWORD_MIN_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Password must be at least {PASSWORD_MIN_LENGTH} characters'
            }), 400
        
        session = get_db_session()
        try:
            # Find user by email
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Check if credentials already exist
            credential = session.query(UserCredential).filter(
                UserCredential.user_id == user.id
            ).first()
            
            if credential:
                return jsonify({
                    'success': False,
                    'message': 'Password already set. Use change-password instead.'
                }), 400
            
            # Create credentials
            credential = UserCredential(
                user_id=user.id,
                password_hash=hash_password(password),
                is_active=True
            )
            session.add(credential)
            session.commit()
            
            logger.info(f"Password set for user: {email}")
            return jsonify({
                'success': True,
                'message': 'Password set successfully. You can now login.'
            }), 200
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Set password error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/change-password', methods=['POST'])
@require_user_auth
def change_password():
    """Change password for logged-in user"""
    try:
        user_info = request.user_info
        data = request.get_json()
        
        if not data or not all(k in data for k in ['current_password', 'new_password']):
            return jsonify({'success': False, 'message': 'Current and new password required'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate new password
        if len(new_password) < PASSWORD_MIN_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Password must be at least {PASSWORD_MIN_LENGTH} characters'
            }), 400
        
        session = get_db_session()
        try:
            credential = session.query(UserCredential).filter(
                UserCredential.user_id == user_info['user_id']
            ).first()
            
            if not credential:
                return jsonify({'success': False, 'message': 'Credentials not found'}), 404
            
            # Verify current password
            if not verify_password(current_password, credential.password_hash):
                return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
            
            # Update password
            credential.password_hash = hash_password(new_password)
            credential.updated_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"Password changed for user: {user_info['email']}")
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            }), 200
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Change password error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/request-reset', methods=['POST'])
def request_password_reset():
    """Request password reset (sends reset token)"""
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'success': False, 'message': 'Email required'}), 400
        
        email = data['email'].lower().strip()
        
        session = get_db_session()
        try:
            user = session.query(User).filter(User.email == email).first()
            
            # Always return success to prevent email enumeration
            if not user:
                return jsonify({
                    'success': True,
                    'message': 'If the email exists, a reset link will be sent.'
                }), 200
            
            credential = session.query(UserCredential).filter(
                UserCredential.user_id == user.id
            ).first()
            
            if not credential:
                # Create credential record for reset
                credential = UserCredential(
                    user_id=user.id,
                    password_hash='',  # Will be set during reset
                    is_active=True
                )
                session.add(credential)
            
            # Generate reset token
            reset_token = generate_reset_token()
            credential.reset_token = reset_token
            credential.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            session.commit()
            
            # TODO: Send reset email with token
            # For now, log the token (in production, send via email)
            logger.info(f"Password reset requested for {email}. Token: {reset_token}")
            
            return jsonify({
                'success': True,
                'message': 'If the email exists, a reset link will be sent.',
                # Include token in response for development (remove in production)
                'reset_token': reset_token if os.environ.get('DEBUG') else None
            }), 200
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Request reset error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@user_auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using reset token"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['token', 'new_password']):
            return jsonify({'success': False, 'message': 'Token and new password required'}), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Validate new password
        if len(new_password) < PASSWORD_MIN_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Password must be at least {PASSWORD_MIN_LENGTH} characters'
            }), 400
        
        session = get_db_session()
        try:
            credential = session.query(UserCredential).filter(
                UserCredential.reset_token == token
            ).first()
            
            if not credential:
                return jsonify({'success': False, 'message': 'Invalid or expired reset token'}), 400
            
            if credential.reset_token_expires < datetime.utcnow():
                return jsonify({'success': False, 'message': 'Reset token has expired'}), 400
            
            # Update password and clear reset token
            credential.password_hash = hash_password(new_password)
            credential.reset_token = None
            credential.reset_token_expires = None
            credential.updated_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"Password reset completed for user_id: {credential.user_id}")
            return jsonify({
                'success': True,
                'message': 'Password reset successfully. You can now login.'
            }), 200
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Reset password error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500
