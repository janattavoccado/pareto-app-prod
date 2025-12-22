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

# Assuming config_loader is available for loading users.json content
from .config_loader import get_user_config

logger = logging.getLogger(__name__)


class UserManager:
    """
    Manages user authentication and lookup from configuration file
    """
    
    def __init__(self):
        """
        Initialize UserManager by loading users data via config_loader.
        """
        self.users_data = None
        self._load_users()
    
    def _load_users(self) -> None:
        """
        Load users from configuration file using config_loader.
        """
        try:
            # Use config_loader to get users data (from Base64 or file)
            config = get_user_config()
            
            if not config:
                logger.error("Users configuration not loaded. Check USER_CONFIG_JSON or configurations/users.json")
                self.users_data = {"users": []}
                return
            
            self.users_data = config
            
            logger.info(f"Loaded {len(self.users_data.get('users', []))} users from configurations/users.json")
        
        except Exception as e:
            logger.error(f"Error loading users configuration: {str(e)}")
            self.users_data = {"users": []}
    
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
        
        Returns:
            str: Email address if user found and enabled, None otherwise
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            # This is the key the calendar client needs to look up calendar_id in users.json
            return user.get("email")
        return None
    
    def get_google_token_path(self, phone_number: str) -> Optional[str]:
        """
        Get path to user's Google API token file (now returns email for client init)
        
        The client is initialized with the user's email, which is then used as the key
        to look up the calendar ID in users.json.
        """
        user = self.get_user_by_phone(phone_number)
        if user:
            # The client needs the user's email to look up the calendar ID in users.json
            email = user.get("email")
            if email:
                return email
            else:
                logger.warning(f"User email not found for {phone_number}")
        return None
    
    def is_user_authorized(self, phone_number: str) -> bool:
        """
        Check if user is authorized (exists and enabled)
        """
        user = self.get_user_by_phone(phone_number)
        return user is not None
    
    def reload_users(self) -> None:
        """
        Reload users from configuration file
        """
        logger.info("Reloading users configuration...")
        self._load_users()


# Create a singleton instance
_user_manager = None


def get_user_manager() -> UserManager:
    """
    Get or create the UserManager instance
    """
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
