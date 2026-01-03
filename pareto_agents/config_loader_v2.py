"""
Configuration Loader v2 - Now with Personal Assistant Config

Reads configurations from:
1. Base64 environment variables (Heroku production)
2. JSON files (Local Windows development)
3. SQLite database (for Google tokens)

New in this version:
- Added AppConfig singleton to hold all loaded configurations.
- Added get_personal_assistant_config() to load settings for the PA agent.

File location: pareto_agents/config_loader_v2.py
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Any

from .database import get_db_session, User
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

class AppConfig:
    """Singleton to hold all application configurations."""
    _instance = None

    # Configuration attributes
    google_client_secrets: Optional[Dict] = None
    openai_api_key: Optional[str] = None
    chatwoot_credentials: Optional[Dict] = None
    personal_assistant_config: Optional[Dict] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_configs(cls):
        """Load all configurations into the singleton."""
        if not cls.is_loaded():
            logger.info("Loading all application configurations...")
            cls.google_client_secrets = ConfigLoaderV2.get_google_client_secrets()
            cls.openai_api_key = ConfigLoaderV2.get_openai_api_key()
            cls.chatwoot_credentials = ConfigLoaderV2.get_chatwoot_credentials()
            cls.personal_assistant_config = ConfigLoaderV2.get_personal_assistant_config()
            logger.info("✅ All configurations loaded.")

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if configurations are already loaded."""
        return all([
            cls.google_client_secrets,
            cls.openai_api_key,
            cls.chatwoot_credentials,
            cls.personal_assistant_config
        ])

class ConfigLoaderV2:
    """Load configuration from environment variables, files, or database."""
    
    @staticmethod
    def _load_json_from_base64(env_var_name: str) -> Optional[Dict]:
        env_value = os.getenv(env_var_name)
        if not env_value:
            return None
        try:
            decoded_bytes = base64.b64decode(env_value)
            decoded_json = decoded_bytes.decode("utf-8")
            return json.loads(decoded_json)
        except Exception as e:
            logger.error(f"Error loading {env_var_name} from Base64: {e}")
            return None
    
    @staticmethod
    def _load_json_from_file(file_path: str) -> Optional[Dict]:
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

    @staticmethod
    def _load_base64_json_or_file(env_var_name: str, local_path: str) -> Optional[Dict]:
        data = ConfigLoaderV2._load_json_from_base64(env_var_name)
        if data: return data
        data = ConfigLoaderV2._load_json_from_file(local_path)
        if data: return data
        logger.warning(f"Config not found for {env_var_name} or {local_path}")
        return None

    @staticmethod
    def get_google_client_secrets() -> Optional[Dict]:
        return ConfigLoaderV2._load_base64_json_or_file(
            env_var_name="GOOGLE_CREDS_JSON",
            local_path="configurations/client_secrets.json"
        )

    @staticmethod
    def get_google_user_token_by_phone(phone_number: str) -> Optional[Dict]:
        session = get_db_session()
        try:
            user = session.query(User).filter_by(phone_number=phone_number).first()
            if user and user.google_token_base64:
                return TokenManager().decode_token(user.google_token_base64)
            return None
        finally:
            session.close()
    
    @staticmethod
    def get_user_calendar_id_by_phone(phone_number: str) -> Optional[str]:
        """Get user's Google Calendar ID from database by phone number."""
        session = get_db_session()
        try:
            user = session.query(User).filter_by(phone_number=phone_number).first()
            if user:
                return user.google_calendar_id
            return None
        finally:
            session.close()

    @staticmethod
    def get_openai_api_key() -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    @staticmethod
    def get_chatwoot_credentials() -> Dict[str, Optional[str]]:
        api_key = os.getenv("CHATWOOT_API_KEY") or os.getenv("CHATWOOT_ACCESS_KEY")
        base_url = os.getenv("CHATWOOT_BASE_URL") or os.getenv("CHATWOOT_API_URL") or "https://pareto-demo-chatwoot-chatwoot.pixpji.easypanel.host"
        return {
            "api_key": api_key,
            "account_id": os.getenv("CHATWOOT_ACCOUNT_ID"),
            "inbox_id": os.getenv("CHATWOOT_INBOX_ID"),
            "base_url": base_url,
        }

    @staticmethod
    def get_personal_assistant_config() -> Dict[str, Any]:
        """
        Get Personal Assistant configuration from env var or file.
        Priority: PA_CONFIG_JSON env var -> users.json -> defaults.
        """
        logger.info("Attempting to load Personal Assistant configuration...")
        
        # Default configuration
        default_config = {
            "model": "gpt-4.1-mini",
            "temperature": 0.7,
            "max_tokens": 2000,
            "daily_summary_email_limit": 7,
        }

        # Load from environment variable
        env_config = ConfigLoaderV2._load_json_from_base64("PA_CONFIG_JSON")
        if env_config:
            default_config.update(env_config)
            logger.info("✅ Personal Assistant config loaded from environment.")
            return default_config

        # Load from general user config file
        user_config_file = ConfigLoaderV2._load_json_from_file("configurations/users.json")
        if user_config_file and "personal_assistant" in user_config_file:
            default_config.update(user_config_file["personal_assistant"])
            logger.info("✅ Personal Assistant config loaded from users.json.")
            return default_config

        logger.info("✅ Personal Assistant config loaded with default values.")
        return default_config

# Helper functions to access configs from the singleton
def get_google_client_secrets(): return AppConfig.google_client_secrets
def get_openai_api_key(): return AppConfig.openai_api_key
def get_chatwoot_credentials(): return AppConfig.chatwoot_credentials
def get_personal_assistant_config(): return AppConfig.personal_assistant_config

# Expose the database token function directly
get_google_user_token_by_phone = ConfigLoaderV2.get_google_user_token_by_phone
get_user_calendar_id_by_phone = ConfigLoaderV2.get_user_calendar_id_by_phone
