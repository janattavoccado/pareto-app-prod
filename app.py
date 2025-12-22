"""
Updated Flask Application with Pareto Agents Integration
Supports both local (file-based) and Heroku (Base64 env vars) configurations
"""

import os
import logging
import sys
from flask import Flask
from dotenv import load_dotenv

# Import config loader for Base64 and file-based configurations
try:
    from pareto_agents.config_loader import (
        get_google_credentials,
        get_user_config,
        get_openai_api_key,
        get_chatwoot_credentials,
        verify_all_configs
    )
except ImportError as e:
    print(f"❌ Error importing config_loader: {e}")
    print("Make sure config_loader.py is in the pareto_agents/ folder")
    sys.exit(1)

# Import blueprints
from pareto_agents.chatwoot_webhook import chatwoot_bp
from webhook_payload_logger import debug_bp

# Load environment variables from .env file (local development only)
# On Heroku, this won't find .env but that's OK - Heroku config vars are used instead
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# ============================================================================
# CONFIGURATION VERIFICATION
# ============================================================================
# This runs on app startup to verify all required configurations are available

def verify_configurations():
    """
    Verify all required configurations are available.
    Works with both local (file-based) and Heroku (Base64 env vars) setups.
    """
    logger.info("=" * 80)
    logger.info("VERIFYING APPLICATION CONFIGURATIONS")
    logger.info("=" * 80)

    # Verify all configs
    all_configs_ok = verify_all_configs()

    if not all_configs_ok:
        logger.warning("⚠️  Some configurations are missing, but app will still start")
        logger.warning("Some features may not work without proper configuration")
    else:
        logger.info("✅ All configurations verified successfully!")

    logger.info("=" * 80)
    return all_configs_ok


# Run configuration verification on startup
try:
    verify_configurations()
except Exception as e:
    logger.error(f"❌ Error during configuration verification: {e}")
    logger.warning("App will continue, but some features may not work")

# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================

# Register debug blueprint (for webhook payload logging)
app.register_blueprint(debug_bp)

# Register the Chatwoot webhook blueprint
app.register_blueprint(chatwoot_bp)

# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def index():
    """
    Root endpoint - returns API status
    """
    return {
        "message": "Valhalla API Server @Heroku",
        "status": "running",
        "version": "1.0.0"
    }, 200


@app.route("/health")
def health():
    """
    Health check endpoint - used by Heroku to verify app is running
    """
    try:
        # Try to load configs to verify they're available
        google_creds = get_google_credentials()
        user_config = get_user_config()
        openai_key = get_openai_api_key()
        chatwoot_creds = get_chatwoot_credentials()

        # Check if critical configs are available
        configs_ok = (
            google_creds is not None and
            user_config is not None and
            openai_key is not None and
            chatwoot_creds.get('api_key') is not None
        )

        return {
            "status": "healthy" if configs_ok else "degraded",
            "service": "Valhalla Flask App",
            "configs": {
                "google_credentials": google_creds is not None,
                "user_config": user_config is not None,
                "openai_api_key": openai_key is not None,
                "chatwoot_credentials": chatwoot_creds.get('api_key') is not None
            }
        }, 200 if configs_ok else 503

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "service": "Valhalla Flask App",
            "error": str(e)
        }, 503


@app.route("/config-status")
def config_status():
    """
    Configuration status endpoint - shows which configs are loaded
    Useful for debugging on Heroku
    """
    try:
        google_creds = get_google_credentials()
        user_config = get_user_config()
        openai_key = get_openai_api_key()
        chatwoot_creds = get_chatwoot_credentials()

        return {
            "environment": "heroku" if os.getenv("DYNO") else "local",
            "configurations": {
                "google_credentials": {
                    "loaded": google_creds is not None,
                    "source": "GOOGLE_CREDS_JSON (Base64)" if os.getenv("GOOGLE_CREDS_JSON") else "configurations/client_secrets.json (file)"
                },
                "user_config": {
                    "loaded": user_config is not None,
                    "source": "USER_CONFIG_JSON (Base64)" if os.getenv("USER_CONFIG_JSON") else "configurations/users.json (file)"
                },
                "openai_api_key": {
                    "loaded": openai_key is not None,
                    "source": "OPENAI_API_KEY (environment variable)"
                },
                "chatwoot_credentials": {
                    "loaded": chatwoot_creds.get('api_key') is not None,
                    "source": "Environment variables"
                }
            }
        }, 200

    except Exception as e:
        logger.error(f"Config status error: {e}")
        return {
            "error": str(e)
        }, 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {
        "error": "Not Found",
        "message": "The requested endpoint does not exist"
    }, 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }, 500


# ============================================================================
# APP STARTUP
# ============================================================================

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("SERVER_PORT", 8000)))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logger.info("=" * 80)
    logger.info(f"Starting Valhalla Flask App")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug: {debug}")
    logger.info(f"Environment: {'Heroku' if os.getenv('DYNO') else 'Local'}")
    logger.info("=" * 80)

    # Start the Flask app
    app.run(host=host, port=port, debug=debug)
