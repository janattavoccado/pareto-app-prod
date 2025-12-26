"""
Database-backed User Management Module

Replaces file-based user management with SQLite database.
Maintains backward compatibility with existing code.

File location: pareto_agents/user_manager_db.py
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from .database import get_db_session, User, Tenant

logger = logging.getLogger(__name__)


class UserManagerDB:
    """
    Database-backed user manager
    Provides same interface as original UserManager but uses SQLite
    """
    
    def __init__(self, tenant_id: Optional[int] = None):
        """
        Initialize UserManager with optional tenant context
        
        Args:
            tenant_id: Tenant ID to filter users. If None, uses first active tenant.
        """
        self.tenant_id = tenant_id
        self._ensure_tenant_context()
    
    def _ensure_tenant_context(self):
        """Ensure we have a valid tenant context"""
        if self.tenant_id is None:
            session = get_db_session()
            try:
                # Get first active tenant
                tenant = session.query(Tenant).filter_by(is_active=True).first()
                if tenant:
                    self.tenant_id = tenant.id
                    logger.info(f"Using default tenant: {tenant.company_name} (ID: {tenant.id})")
                else:
                    logger.error("No active tenants found in database")
                    raise ValueError("No active tenants found")
            finally:
                session.close()
    
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by phone number
        
        Args:
            phone_number: Phone number to search for (e.g., "+46735408023")
            
        Returns:
            dict: User information if found and enabled, None otherwise
        """
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(
                tenant_id=self.tenant_id,
                phone_number=phone_number,
                is_enabled=True
            ).first()
            
            if user:
                logger.info(f"User found and enabled: {user.full_name} ({phone_number})")
                return self._user_to_dict(user)
            else:
                # Check if user exists but is disabled
                disabled_user = session.query(User).filter_by(
                    tenant_id=self.tenant_id,
                    phone_number=phone_number
                ).first()
                
                if disabled_user:
                    logger.info(f"User found but disabled: {phone_number}")
                else:
                    logger.info(f"User not found: {phone_number}")
                
                return None
        
        except Exception as e:
            logger.error(f"Error querying user by phone: {e}")
            return None
        
        finally:
            session.close()
    
    def get_user_full_name(self, phone_number: str) -> str:
        """
        Get user's full name by phone number
        
        Args:
            phone_number: Phone number to search for
            
        Returns:
            str: Full name if user found and enabled, empty string otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            return user.get('full_name', '')
        return ""
    
    def get_user_email(self, phone_number: str) -> Optional[str]:
        """
        Get user's email by phone number
        
        Args:
            phone_number: Phone number to search for
            
        Returns:
            str: Email address if user found and enabled, None otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            return user.get('email')
        return None
    
    def get_google_token_path(self, phone_number: str) -> Optional[str]:
        """
        Get path to user's Google API token file
        
        Args:
            phone_number: Phone number to search for
            
        Returns:
            str: Path to token file if user found and enabled, None otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            return user.get('google_token_path')
        return None
    
    def is_user_authorized(self, phone_number: str) -> bool:
        """
        Check if user is authorized (exists and enabled)
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            bool: True if user is authorized, False otherwise
        """
        user = self.get_user_by_phone(phone_number)
        return user is not None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all enabled users for the tenant
        
        Returns:
            List of user dictionaries
        """
        session = get_db_session()
        
        try:
            users = session.query(User).filter_by(
                tenant_id=self.tenant_id,
                is_enabled=True
            ).all()
            
            return [self._user_to_dict(user) for user in users]
        
        except Exception as e:
            logger.error(f"Error querying all users: {e}")
            return []
        
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by database ID
        
        Args:
            user_id: User database ID
            
        Returns:
            User dictionary or None
        """
        session = get_db_session()
        
        try:
            user = session.query(User).filter_by(
                id=user_id,
                tenant_id=self.tenant_id,
                is_enabled=True
            ).first()
            
            if user:
                return self._user_to_dict(user)
            return None
        
        except Exception as e:
            logger.error(f"Error querying user by ID: {e}")
            return None
        
        finally:
            session.close()
    
    @staticmethod
    def _user_to_dict(user: User) -> Dict[str, Any]:
        """
        Convert User ORM object to dictionary
        
        Args:
            user: User ORM instance
            
        Returns:
            Dictionary representation of user
        """
        return {
            'id': user.id,
            'tenant_id': user.tenant_id,
            'phone_number': user.phone_number,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'email': user.email,
            'enabled': user.is_enabled,
            'google_token_path': user.google_token_path,
            'google_token_json': user.google_token_json,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }


# ============================================================================
# Singleton Instance Management
# ============================================================================

_user_manager_db: Optional[UserManagerDB] = None


def get_user_manager_db(tenant_id: Optional[int] = None) -> UserManagerDB:
    """
    Get or create the UserManager instance
    
    Args:
        tenant_id: Tenant ID to filter users. If None, uses first active tenant.
        
    Returns:
        UserManagerDB instance
    """
    global _user_manager_db
    if _user_manager_db is None:
        _user_manager_db = UserManagerDB(tenant_id)
    return _user_manager_db


def reset_user_manager():
    """Reset the singleton instance (useful for testing)"""
    global _user_manager_db
    _user_manager_db = None


# ============================================================================
# Backward Compatibility Layer
# ============================================================================

def get_user_manager(config_path: str = "configurations/users.json") -> UserManagerDB:
    """
    Backward compatible function to get user manager
    
    Signature matches original UserManager for drop-in replacement.
    The config_path parameter is ignored (kept for compatibility).
    
    Args:
        config_path: Ignored (kept for backward compatibility)
        
    Returns:
        UserManagerDB instance
    """
    return get_user_manager_db()


if __name__ == '__main__':
    # Test script
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test user manager
    manager = get_user_manager_db()
    
    # Get all users
    all_users = manager.get_all_users()
    logger.info(f"Total users: {len(all_users)}")
    
    for user in all_users:
        logger.info(f"User: {user['full_name']} ({user['phone_number']}) - Enabled: {user['enabled']}")
    
    # Test lookup
    test_phone = "+46735408023"
    user = manager.get_user_by_phone(test_phone)
    if user:
        logger.info(f"Found user: {user['full_name']} ({user['email']})")
    else:
        logger.info(f"User not found: {test_phone}")
