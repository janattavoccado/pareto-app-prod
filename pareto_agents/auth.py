"""
Authentication Module

Handles administrator authentication, session management, and password security.

File location: pareto_agents/auth.py
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from functools import wraps

from sqlalchemy.orm import Session
from flask import request, jsonify

try:
    from bcrypt import hashpw, gensalt, checkpw
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("⚠️  bcrypt not installed, falling back to plain text passwords (NOT SECURE!)")

from .database import get_db_session, Administrator, AdminSession, AuditLog

logger = logging.getLogger(__name__)

# Configuration
SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', 24))
SESSION_TOKEN_LENGTH = 64


# ============================================================================
# Password Management
# ============================================================================

class PasswordManager:
    """Handles password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        if BCRYPT_AVAILABLE:
            try:
                password_bytes = password.encode('utf-8')
                hashed = hashpw(password_bytes, gensalt())
                return hashed.decode('utf-8')
            except Exception as e:
                logger.error(f"Error hashing password: {e}")
                raise
        else:
            logger.warning("⚠️  Using plain text password (NOT SECURE!)")
            return password
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password: Plain text password to verify
            password_hash: Hashed password to check against
            
        Returns:
            True if password matches, False otherwise
        """
        if not password or not password_hash:
            return False
        
        if BCRYPT_AVAILABLE:
            try:
                password_bytes = password.encode('utf-8')
                hash_bytes = password_hash.encode('utf-8')
                return checkpw(password_bytes, hash_bytes)
            except Exception as e:
                logger.error(f"Error verifying password: {e}")
                return False
        else:
            # Fallback to plain text comparison (NOT SECURE!)
            return password == password_hash


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """Handles administrator session creation and validation"""
    
    @staticmethod
    def create_session(
        admin_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new session for an administrator
        
        Args:
            admin_id: Administrator ID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Session token or None if creation failed
        """
        session = get_db_session()
        
        try:
            # Generate secure session token
            session_token = secrets.token_urlsafe(SESSION_TOKEN_LENGTH)
            
            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
            
            # Create session record
            admin_session = AdminSession(
                admin_id=admin_id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at
            )
            
            session.add(admin_session)
            session.commit()
            
            logger.info(f"✅ Session created for admin {admin_id}")
            return session_token
        
        except Exception as e:
            logger.error(f"❌ Error creating session: {e}")
            session.rollback()
            return None
        
        finally:
            session.close()
    
    @staticmethod
    def validate_session(session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token
        
        Args:
            session_token: Session token to validate
            
        Returns:
            Dictionary with admin info if valid, None otherwise
        """
        session = get_db_session()
        
        try:
            # Find session
            admin_session = session.query(AdminSession).filter_by(
                session_token=session_token
            ).first()
            
            if not admin_session:
                logger.warning(f"❌ Session not found: {session_token[:10]}...")
                return None
            
            # Check if expired
            if admin_session.is_expired:
                logger.warning(f"❌ Session expired: {session_token[:10]}...")
                session.delete(admin_session)
                session.commit()
                return None
            
            # Get admin info
            admin = admin_session.administrator
            
            if not admin or not admin.is_active:
                logger.warning(f"❌ Admin not active: {admin.username if admin else 'Unknown'}")
                return None
            
            logger.info(f"✅ Session valid for admin: {admin.username}")
            
            return {
                'admin_id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'full_name': admin.full_name,
                'session_id': admin_session.id,
                'expires_at': admin_session.expires_at.isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Error validating session: {e}")
            return None
        
        finally:
            session.close()
    
    @staticmethod
    def destroy_session(session_token: str) -> bool:
        """
        Destroy a session (logout)
        
        Args:
            session_token: Session token to destroy
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        
        try:
            admin_session = session.query(AdminSession).filter_by(
                session_token=session_token
            ).first()
            
            if admin_session:
                session.delete(admin_session)
                session.commit()
                logger.info(f"✅ Session destroyed: {session_token[:10]}...")
                return True
            else:
                logger.warning(f"❌ Session not found: {session_token[:10]}...")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error destroying session: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions from database"""
        session = get_db_session()
        
        try:
            expired_count = session.query(AdminSession).filter(
                AdminSession.expires_at < datetime.utcnow()
            ).delete()
            
            session.commit()
            
            if expired_count > 0:
                logger.info(f"✅ Cleaned up {expired_count} expired sessions")
            
            return expired_count
        
        except Exception as e:
            logger.error(f"❌ Error cleaning up sessions: {e}")
            session.rollback()
            return 0
        
        finally:
            session.close()


# ============================================================================
# Authentication Service
# ============================================================================

class AuthenticationService:
    """Main authentication service"""
    
    @staticmethod
    def login(username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Tuple[bool, Optional[str], str]:
        """
        Authenticate an administrator
        
        Args:
            username: Administrator username
            password: Administrator password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (success, session_token, message)
        """
        session = get_db_session()
        
        try:
            # Find admin by username
            admin = session.query(Administrator).filter_by(username=username).first()
            
            if not admin:
                logger.warning(f"❌ Login failed: user not found - {username}")
                return False, None, "Invalid username or password"
            
            if not admin.is_active:
                logger.warning(f"❌ Login failed: admin inactive - {username}")
                return False, None, "Account is inactive"
            
            # Verify password
            if not PasswordManager.verify_password(password, admin.password_hash):
                logger.warning(f"❌ Login failed: invalid password - {username}")
                return False, None, "Invalid username or password"
            
            # Create session
            session_token = SessionManager.create_session(
                admin_id=admin.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if not session_token:
                return False, None, "Failed to create session"
            
            # Update last login
            admin.last_login = datetime.utcnow()
            session.commit()
            
            logger.info(f"✅ Login successful: {username}")
            return True, session_token, "Login successful"
        
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False, None, "An error occurred during login"
        
        finally:
            session.close()
    
    @staticmethod
    def logout(session_token: str) -> Tuple[bool, str]:
        """
        Logout an administrator
        
        Args:
            session_token: Session token
            
        Returns:
            Tuple of (success, message)
        """
        if SessionManager.destroy_session(session_token):
            logger.info("✅ Logout successful")
            return True, "Logout successful"
        else:
            logger.warning("❌ Logout failed: session not found")
            return False, "Session not found"
    
    @staticmethod
    def change_password(admin_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change administrator password
        
        Args:
            admin_id: Administrator ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        session = get_db_session()
        
        try:
            admin = session.query(Administrator).filter_by(id=admin_id).first()
            
            if not admin:
                return False, "Administrator not found"
            
            # Verify old password
            if not PasswordManager.verify_password(old_password, admin.password_hash):
                return False, "Current password is incorrect"
            
            # Validate new password
            if not new_password or len(new_password) < 8:
                return False, "New password must be at least 8 characters"
            
            # Hash and update password
            admin.password_hash = PasswordManager.hash_password(new_password)
            session.commit()
            
            logger.info(f"✅ Password changed for admin: {admin.username}")
            return True, "Password changed successfully"
        
        except Exception as e:
            logger.error(f"❌ Error changing password: {e}")
            session.rollback()
            return False, "An error occurred"
        
        finally:
            session.close()


# ============================================================================
# Flask Decorators
# ============================================================================

def require_auth(f):
    """
    Decorator to require authentication for Flask routes
    
    Usage:
        @app.route('/admin/dashboard')
        @require_auth
        def admin_dashboard():
            admin_info = request.admin_info
            return jsonify(admin_info)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from header or cookie
        session_token = None
        
        # Try Authorization header first
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        
        # Try cookie as fallback
        if not session_token:
            session_token = request.cookies.get('session_token')
        
        if not session_token:
            logger.warning("❌ No session token provided")
            return jsonify({'error': 'Unauthorized', 'message': 'No session token provided'}), 401
        
        # Validate session
        admin_info = SessionManager.validate_session(session_token)
        
        if not admin_info:
            logger.warning("❌ Invalid or expired session token")
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid or expired session'}), 401
        
        # Attach admin info to request
        request.admin_info = admin_info
        request.session_token = session_token
        
        return f(*args, **kwargs)
    
    return decorated_function


if __name__ == '__main__':
    # Test script
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test password hashing
    logger.info("Testing password hashing...")
    password = "test123456"
    hashed = PasswordManager.hash_password(password)
    logger.info(f"Original: {password}")
    logger.info(f"Hashed: {hashed}")
    logger.info(f"Verify: {PasswordManager.verify_password(password, hashed)}")
    
    # Test login
    logger.info("\nTesting login...")
    success, token, message = AuthenticationService.login('admin', 'admin123')
    logger.info(f"Login result: {success} - {message}")
    if token:
        logger.info(f"Session token: {token[:20]}...")
        
        # Test session validation
        logger.info("\nTesting session validation...")
        admin_info = SessionManager.validate_session(token)
        if admin_info:
            logger.info(f"Admin info: {admin_info}")
        
        # Test logout
        logger.info("\nTesting logout...")
        success, message = AuthenticationService.logout(token)
        logger.info(f"Logout result: {success} - {message}")
