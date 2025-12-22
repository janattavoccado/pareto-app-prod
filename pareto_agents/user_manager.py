"""
User Management Module
Handles user authentication and lookup from users.json configuration file

File location: pareto_agents/user_manager.py
"""

import json
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class UserManager:
    """
    Manages user authentication and lookup from configuration file
    """
    
    def __init__(self, config_path: str = "configurations/users.json"):
        """
        Initialize UserManager with configuration file path
        
        Args:
            config_path (str): Path to users.json configuration file
        """
        self.config_path = config_path
        self.users_data = None
        self._load_users()
    
    def _load_users(self) -> None:
        """
        Load users from configuration file
        
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            json.JSONDecodeError: If configuration file is invalid JSON
        """
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}\n"
                    f"Please create {self.config_path} with user configurations."
                )
            
            with open(self.config_path, 'r') as f:
                self.users_data = json.load(f)
            
            logger.info(f"Loaded {len(self.users_data.get('users', []))} users from {self.config_path}")
        
        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config_path}: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Error loading users configuration: {str(e)}")
            raise
    
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by phone number
        
        Args:
            phone_number (str): Phone number to search for (e.g., "+46735408023")
            
        Returns:
            dict: User information if found and enabled, None otherwise
        """
        if not self.users_data:
            logger.warning("Users data not loaded")
            return None
        
        users = self.users_data.get("users", [])
        
        for user in users:
            if user.get("phone_number") == phone_number:
                # Check if user is enabled
                if not user.get("enabled", False):
                    logger.info(f"User {phone_number} found but disabled")
                    return None
                
                logger.info(f"User {phone_number} found and enabled: {user.get('first_name')} {user.get('last_name')}")
                return user
        
        logger.info(f"User {phone_number} not found in configuration")
        return None
    
    def get_user_full_name(self, phone_number: str) -> str:
        """
        Get user's full name by phone number
        
        Args:
            phone_number (str): Phone number to search for
            
        Returns:
            str: Full name if user found and enabled, empty string otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            first_name = user.get("first_name", "")
            last_name = user.get("last_name", "")
            return f"{first_name} {last_name}".strip()
        return ""
    
    def get_user_email(self, phone_number: str) -> Optional[str]:
        """
        Get user's email by phone number
        
        Args:
            phone_number (str): Phone number to search for
            
        Returns:
            str: Email address if user found and enabled, None otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            return user.get("email")
        return None
    
    def get_google_token_path(self, phone_number: str) -> Optional[str]:
        """
        Get path to user's Google API token file
        
        Args:
            phone_number (str): Phone number to search for
            
        Returns:
            str: Path to token file if user found and enabled, None otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            token_path = user.get("google_token_path")
            if token_path and os.path.exists(token_path):
                return token_path
            else:
                logger.warning(f"Google token file not found for {phone_number}: {token_path}")
        return None
    
    def is_user_authorized(self, phone_number: str) -> bool:
        """
        Check if user is authorized (exists and enabled)
        
        Args:
            phone_number (str): Phone number to check
            
        Returns:
            bool: True if user is authorized, False otherwise
        """
        user = self.get_user_by_phone(phone_number)
        return user is not None
    
    def reload_users(self) -> None:
        """
        Reload users from configuration file
        Useful for refreshing configuration without restarting the app
        """
        logger.info("Reloading users configuration...")
        self._load_users()


# Create a singleton instance
_user_manager = None


def get_user_manager(config_path: str = "configurations/users.json") -> UserManager:
    """
    Get or create the UserManager instance
    
    Args:
        config_path (str): Path to users.json configuration file
        
    Returns:
        UserManager: The user manager instance
    """
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager(config_path)
    return _user_manager
