"""
User Manager with Database-backed Token Support (v2)

Manages users and their Google tokens stored in the database as Base64 strings.
Replaces file-based token management with database storage.

File location: pareto_agents/user_manager_db_v2.py
"""

import json
import logging
from typing import Optional, Dict, Any

from .database import get_db_session, User
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class UserManagerDBv2:
    """Database-backed user manager with Base64 token support"""
    
    def __init__(self):
        """Initialize user manager"""
        self.token_manager = TokenManager()
    
    def get_user_by_phone(self, phone_number: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get user by phone number
        
        Args:
            phone_number: User's phone number
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            User dictionary or None if not found
        """
        session = get_db_session()
        try:
            query = session.query(User).filter_by(phone_number=phone_number)
            
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            user = query.first()
            
            if user:
                return self._user_to_dict(user)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting user by phone: {e}")
            return None
        
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary or None if not found
        """
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if user:
                return self._user_to_dict(user)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        
        finally:
            session.close()
    
    def get_users_by_tenant(self, tenant_id: int, enabled_only: bool = False) -> list:
        """
        Get all users for a tenant
        
        Args:
            tenant_id: Tenant ID
            enabled_only: If True, return only enabled users
            
        Returns:
            List of user dictionaries
        """
        session = get_db_session()
        try:
            query = session.query(User).filter_by(tenant_id=tenant_id)
            
            if enabled_only:
                query = query.filter_by(is_enabled=True)
            
            users = query.all()
            
            return [self._user_to_dict(u) for u in users]
        
        except Exception as e:
            logger.error(f"Error getting users by tenant: {e}")
            return []
        
        finally:
            session.close()
    
    def is_user_authorized(self, phone_number: str, tenant_id: Optional[int] = None) -> bool:
        """
        Check if user is authorized (enabled and exists)
        
        Args:
            phone_number: User's phone number
            tenant_id: Optional tenant ID
            
        Returns:
            True if user is authorized, False otherwise
        """
        user = self.get_user_by_phone(phone_number, tenant_id)
        
        if not user:
            logger.warning(f"User not found: {phone_number}")
            return False
        
        if not user.get('is_enabled'):
            logger.warning(f"User is disabled: {phone_number}")
            return False
        
        return True
    
    def get_user_google_token(self, phone_number: str, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get user's Google token (decoded from Base64)
        
        Args:
            phone_number: User's phone number
            tenant_id: Optional tenant ID
            
        Returns:
            Decoded token dictionary or None if not found
        """
        user = self.get_user_by_phone(phone_number, tenant_id)
        
        if not user:
            logger.warning(f"User not found: {phone_number}")
            return None
        
        if not user.get('google_token_base64'):
            logger.warning(f"User has no Google token: {phone_number}")
            return None
        
        try:
            token = self.token_manager.decode_token(user['google_token_base64'])
            logger.info(f"✅ Retrieved Google token for user: {phone_number}")
            return token
        
        except Exception as e:
            logger.error(f"Error decoding Google token for {phone_number}: {e}")
            return None
    
    def set_user_google_token(self, user_id: int, token_dict: Dict[str, Any]) -> bool:
        """
        Set user's Google token (encode to Base64 and store in database)
        
        Args:
            user_id: User ID
            token_dict: Token dictionary to store
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                return False
            
            # Encode token to Base64
            base64_token = self.token_manager.encode_token(token_dict)
            
            # Store in database
            user.google_token_base64 = base64_token
            session.commit()
            
            logger.info(f"✅ Set Google token for user: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error setting Google token for user {user_id}: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    def set_user_google_token_by_phone(self, phone_number: str, token_dict: Dict[str, Any], tenant_id: Optional[int] = None) -> bool:
        """
        Set user's Google token by phone number
        
        Args:
            phone_number: User's phone number
            token_dict: Token dictionary to store
            tenant_id: Optional tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_phone(phone_number, tenant_id)
        
        if not user:
            logger.warning(f"User not found: {phone_number}")
            return False
        
        return self.set_user_google_token(user['id'], token_dict)
    
    def delete_user_google_token(self, user_id: int) -> bool:
        """
        Delete user's Google token
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"User not found: {user_id}")
                return False
            
            user.google_token_base64 = None
            session.commit()
            
            logger.info(f"✅ Deleted Google token for user: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting Google token for user {user_id}: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    def has_google_token(self, phone_number: str, tenant_id: Optional[int] = None) -> bool:
        """
        Check if user has a Google token configured
        
        Args:
            phone_number: User's phone number
            tenant_id: Optional tenant ID
            
        Returns:
            True if user has a token, False otherwise
        """
        user = self.get_user_by_phone(phone_number, tenant_id)
        
        if not user:
            return False
        
        return bool(user.get('google_token_base64'))
    
    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """
        Convert User model to dictionary
        
        Args:
            user: User model instance
            
        Returns:
            User dictionary
        """
        return {
            'id': user.id,
            'tenant_id': user.tenant_id,
            'phone_number': user.phone_number,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.full_name,
            'email': user.email,
            'is_enabled': user.is_enabled,
            'google_token_base64': user.google_token_base64,
            'has_google_token': user.has_google_token(),
            'google_token_updated_at': user.google_token_updated_at.isoformat() if user.google_token_updated_at else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_user_manager_instance: Optional[UserManagerDBv2] = None


def get_user_manager_db_v2() -> UserManagerDBv2:
    """
    Get or create singleton instance of UserManagerDBv2
    
    Returns:
        UserManagerDBv2 instance
    """
    global _user_manager_instance
    if _user_manager_instance is None:
        _user_manager_instance = UserManagerDBv2()
    return _user_manager_instance


if __name__ == '__main__':
    # Test user manager
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = get_user_manager_db_v2()
    logger.info("User manager initialized successfully")
