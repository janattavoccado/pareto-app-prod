"""
Credentials Helper Module

Reads Google credentials from environment variables or files.
Works seamlessly on both local development and Heroku.

Priority:
1. Environment variable (GOOGLE_CREDENTIALS_JSON) - Heroku
2. File (configurations/client_secrets.json) - Local development
"""

import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_google_credentials():
    """
    Get Google credentials from environment variable or file.
    
    Returns:
        dict: Google credentials dictionary
        None: If credentials not found
    """
    
    # Try environment variable first (Heroku production)
    env_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if env_creds:
        try:
            logger.info("✅ Loading Google credentials from GOOGLE_CREDENTIALS_JSON env var")
            return json.loads(env_creds)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
            return None
    
    # Fall back to files (local development)
    creds_files = [
        'configurations/client_secrets.json',
        'configurations/tokens/jan_avoccado_pareto.json',
    ]
    
    for creds_file in creds_files:
        creds_path = Path(creds_file)
        if creds_path.exists():
            try:
                logger.info(f"✅ Loading Google credentials from file: {creds_file}")
                with open(creds_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Could not read {creds_file}: {e}")
                continue
    
    # No credentials found
    logger.error("❌ No Google credentials found!")
    logger.error("   Set GOOGLE_CREDENTIALS_JSON env var (Heroku)")
    logger.error("   OR create configurations/client_secrets.json (local)")
    return None


def get_google_calendar_id():
    """
    Get Google Calendar ID from environment or config file.
    
    Returns:
        str: Google Calendar ID
        None: If not found
    """
    
    # Try environment first
    calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
    if calendar_id:
        logger.info(f"✅ Using GOOGLE_CALENDAR_ID from environment: {calendar_id}")
        return calendar_id
    
    # Try from credentials file
    creds = get_google_credentials()
    if creds and 'calendar_id' in creds:
        logger.info(f"✅ Using calendar_id from credentials: {creds['calendar_id']}")
        return creds['calendar_id']
    
    logger.error("❌ No Google Calendar ID found!")
    logger.error("   Set GOOGLE_CALENDAR_ID env var")
    logger.error("   OR add 'calendar_id' to credentials JSON")
    return None


def get_google_timezone():
    """
    Get timezone from environment or default.
    
    Returns:
        str: Timezone string (e.g., 'Europe/Zagreb')
    """
    
    timezone = os.getenv('GOOGLE_CALENDAR_TIMEZONE', 'Europe/Zagreb')
    logger.info(f"✅ Using timezone: {timezone}")
    return timezone


def get_openai_api_key():
    """
    Get OpenAI API key from environment.
    
    Returns:
        str: OpenAI API key
        None: If not found
    """
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        logger.info("✅ OpenAI API key found")
        return api_key
    
    logger.error("❌ OPENAI_API_KEY not found!")
    logger.error("   Set OPENAI_API_KEY env var")
    return None


def get_chatwoot_credentials():
    """
    Get Chatwoot credentials from environment.
    
    Returns:
        dict: Chatwoot credentials
    """
    
    creds = {
        'api_key': os.getenv('CHATWOOT_API_KEY'),
        'account_id': os.getenv('CHATWOOT_ACCOUNT_ID'),
        'inbox_id': os.getenv('CHATWOOT_INBOX_ID'),
        'base_url': os.getenv('CHATWOOT_BASE_URL', 'https://pareto-demo-chatwoot-chatwoot.pixpji.easypanel.host'),
    }
    
    if creds['api_key'] and creds['account_id']:
        logger.info("✅ Chatwoot credentials found")
        return creds
    
    logger.error("❌ Chatwoot credentials not found!")
    logger.error("   Set CHATWOOT_API_KEY and CHATWOOT_ACCOUNT_ID env vars")
    return None


def verify_all_credentials():
    """
    Verify all required credentials are available.
    
    Returns:
        bool: True if all credentials found, False otherwise
    """
    
    logger.info("=" * 60)
    logger.info("VERIFYING ALL CREDENTIALS")
    logger.info("=" * 60)
    
    all_good = True
    
    # Check Google credentials
    if not get_google_credentials():
        all_good = False
    
    # Check Google Calendar ID
    if not get_google_calendar_id():
        all_good = False
    
    # Check OpenAI API key
    if not get_openai_api_key():
        all_good = False
    
    # Check Chatwoot credentials
    chatwoot = get_chatwoot_credentials()
    if not chatwoot.get('api_key') or not chatwoot.get('account_id'):
        all_good = False
    
    if all_good:
        logger.info("=" * 60)
        logger.info("✅ ALL CREDENTIALS VERIFIED!")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("❌ SOME CREDENTIALS MISSING!")
        logger.warning("=" * 60)
    
    return all_good


if __name__ == '__main__':
    # Test script
    logging.basicConfig(level=logging.INFO)
    verify_all_credentials()
