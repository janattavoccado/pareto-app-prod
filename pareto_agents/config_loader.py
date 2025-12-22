"""
Configuration Loader Module

Reads configurations from:
1. Base64 environment variables (Heroku production)
2. JSON files (Local Windows development)

Supports:
- Google credentials (client_secrets.json)
- User configuration (users.json)
- OpenAI API key
- Chatwoot credentials
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load configuration from environment variables or files."""
    
    @staticmethod
    def _load_json_from_base64(env_var_name: str) -> Optional[Dict]:
        """
        Load JSON from Base64 encoded environment variable.
        
        Args:
            env_var_name: Name of environment variable containing Base64 JSON
            
        Returns:
            Parsed JSON dictionary or None
        """
        env_value = os.getenv(env_var_name)
        
        if not env_value:
            logger.debug(f"Environment variable {env_var_name} not found")
            return None
        
        try:
            # Decode Base64
            decoded_bytes = base64.b64decode(env_value)
            decoded_json = decoded_bytes.decode('utf-8')
            
            # Parse JSON
            parsed = json.loads(decoded_json)
            logger.info(f"✅ Loaded {env_var_name} from Base64 environment variable")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {env_var_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading {env_var_name}: {e}")
            return None
    
    @staticmethod
    def _load_json_from_file(file_path: str) -> Optional[Dict]:
        """
        Load JSON from file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON dictionary or None
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.debug(f"File not found: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✅ Loaded {file_path} from file")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading {file_path}: {e}")
            return None
    
    @staticmethod
    def _load_base64_json_or_file(env_var_name: str, local_path: str) -> Optional[Dict]:
        """Generic function to load Base64 env var or local JSON file."""
        # 1. Try loading from Base64 environment variable
        data = ConfigLoader._load_json_from_base64(env_var_name)
        if data:
            return data

        # 2. Fallback to local file
        data = ConfigLoader._load_json_from_file(local_path)
        if data:
            return data
            
        logger.warning(f"Data not found for {env_var_name} (or local file {local_path})")
        return None

    @staticmethod
    def get_google_client_secrets() -> Optional[Dict]:
        """Loads Google client secrets (client_secrets.json)"""
        logger.info("Attempting to load Google Client Secrets...")
        return ConfigLoader._load_base64_json_or_file(
            env_var_name='GOOGLE_CLIENT_SECRETS_JSON',
            local_path='configurations/client_secrets.json'
        )

    @staticmethod
    def get_google_user_token() -> Optional[Dict]:
        """Loads Google user token (jan_avoccado_pareto.json)"""
        logger.info("Attempting to load Google User Token...")
        return ConfigLoader._load_base64_json_or_file(
            env_var_name='GOOGLE_USER_TOKEN_JSON',
            local_path='configurations/tokens/jan_avoccado_pareto.json'
        )
    
    @staticmethod
    def get_user_config() -> Optional[Dict]:
        """
        Get user configuration from Base64 env var or file.
        
        Priority:
        1. USER_CONFIG_JSON environment variable (Base64, Heroku)
        2. configurations/users.json file (Local)
        
        Returns:
            User configuration dictionary or None
        """
        
        logger.info("Attempting to load user configuration...")
        return ConfigLoader._load_base64_json_or_file(
            env_var_name='USER_CONFIG_JSON',
            local_path='configurations/users.json'
        )
    
    @staticmethod
    def get_openai_api_key() -> Optional[str]:
        """
        Get OpenAI API key from environment.
        
        Returns:
            OpenAI API key or None
        """
        api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key:
            logger.info("✅ OpenAI API key found in environment")
            return api_key
        
        logger.error("❌ OPENAI_API_KEY not found in environment!")
        return None
    
    @staticmethod
    def get_chatwoot_credentials() -> Dict[str, Optional[str]]:
        """
        Get Chatwoot credentials from environment.
        
        Supports both naming conventions:
        - Standard: CHATWOOT_API_KEY, CHATWOOT_BASE_URL
        - Alternative: CHATWOOT_ACCESS_KEY, CHATWOOT_API_URL
        
        Returns:
            Dictionary with Chatwoot credentials
        """
        # Try standard names first
        api_key = os.getenv('CHATWOOT_API_KEY')
        base_url = os.getenv('CHATWOOT_BASE_URL')
        
        # Fall back to alternative names
        if not api_key:
            api_key = os.getenv('CHATWOOT_ACCESS_KEY')
        if not base_url:
            base_url = os.getenv('CHATWOOT_API_URL')
        
        # Use default if still not found
        if not base_url:
            base_url = 'https://pareto-demo-chatwoot-chatwoot.pixpji.easypanel.host'
        
        creds = {
            'api_key': api_key,
            'account_id': os.getenv('CHATWOOT_ACCOUNT_ID'),
            'inbox_id': os.getenv('CHATWOOT_INBOX_ID'),
            'base_url': base_url,
        }
        
        if creds['api_key'] and creds['account_id']:
            logger.info("✅ Chatwoot credentials found in environment")
            logger.info(f"   API Key source: {'CHATWOOT_API_KEY' if os.getenv('CHATWOOT_API_KEY') else 'CHATWOOT_ACCESS_KEY'}")
            logger.info(f"   Base URL source: {'CHATWOOT_BASE_URL' if os.getenv('CHATWOOT_BASE_URL') else 'CHATWOOT_API_URL'}")
            return creds
        
        logger.error("❌ Chatwoot credentials not found!")
        logger.error("   Set CHATWOOT_API_KEY (or CHATWOOT_ACCESS_KEY) env var")
        logger.error("   Set CHATWOOT_ACCOUNT_ID env var")
        logger.error("   Optionally set CHATWOOT_BASE_URL (or CHATWOOT_API_URL)")
        return creds
    
    @staticmethod
    def verify_all_configs() -> bool:
        """
        Verify all required configurations are available.
        
        Returns:
            True if all configs found, False otherwise
        """
        logger.info("=" * 70)
        logger.info("VERIFYING ALL CONFIGURATIONS")
        logger.info("=" * 70)
        
        all_good = True
        
        # Check Google credentials
        if not ConfigLoader.get_google_client_secrets():
            all_good = False
        if not ConfigLoader.get_google_user_token():
            all_good = False
        
        # Check user config
        if not ConfigLoader.get_user_config():
            all_good = False
        
        # Check OpenAI API key
        if not ConfigLoader.get_openai_api_key():
            all_good = False
        
        # Check Chatwoot credentials
        chatwoot = ConfigLoader.get_chatwoot_credentials()
        if not chatwoot.get('api_key') or not chatwoot.get('account_id'):
            all_good = False
        
        if all_good:
            logger.info("=" * 70)
            logger.info("✅ ALL CONFIGURATIONS VERIFIED!")
            logger.info("=" * 70)
        else:
            logger.warning("=" * 70)
            logger.warning("❌ SOME CONFIGURATIONS MISSING!")
            logger.warning("=" * 70)
        
        return all_good


# Convenience functions for easy import
def get_google_credentials() -> Optional[Dict]:
    """Get Google credentials."""
    return ConfigLoader.get_google_credentials()


def get_user_config() -> Optional[Dict]:
    """Get user configuration."""
    return ConfigLoader.get_user_config()


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key."""
    return ConfigLoader.get_openai_api_key()


def get_chatwoot_credentials() -> Dict[str, Optional[str]]:
    """Get Chatwoot credentials."""
    return ConfigLoader.get_chatwoot_credentials()


def verify_all_configs() -> bool:
    """Verify all configurations."""
    return ConfigLoader.verify_all_configs()


if __name__ == '__main__':
    # Test script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    verify_all_configs()
