"""
Flask Application Entry Point - With SQLite Database Integration

This file has been updated to:
1. Initialize SQLite database
2. Register authentication routes
3. Maintain backward compatibility with existing Chatwoot webhook
4. Support both JSON (fallback) and SQLite user management

File location: app_new.py (rename to app.py after testing)
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory

# Database and authentication imports
from pareto_agents.database import get_db_manager
from pareto_agents.auth_routes import auth_bp
from pareto_agents.admin_routes import admin_bp
from pareto_agents.migrate_users import migrate_users_from_json

# Existing imports from the original app
from pareto_agents.config_loader import (
    get_google_client_secrets,
    get_google_user_token,
    get_user_config,
    verify_all_configs
)
from pareto_agents.chatwoot_webhook import webhook_handler

# --- Configuration ---
IS_HEROKU = 'DYNO' in os.environ
ENVIRONMENT = 'Heroku Production' if IS_HEROKU else 'Local Development'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Starting Flask app in {ENVIRONMENT} environment.")

# --- App Initialization ---
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# --- Database Initialization ---
logger.info("Initializing SQLite database...")
try:
    db_manager = get_db_manager()
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.error(f"❌ Database initialization failed: {e}")
    raise

# --- User Migration (First Run) ---
# Check if migration is needed
if os.path.exists('configurations/users.json'):
    logger.info("Detected users.json - checking if migration is needed...")
    try:
        from pareto_agents.database import get_db_session, User
        session = get_db_session()
        user_count = session.query(User).count()
        session.close()
        
        if user_count == 0:
            logger.info("Database is empty - running migration from users.json...")
            if migrate_users_from_json(dry_run=False):
                logger.info("✅ Migration completed successfully")
            else:
                logger.warning("⚠️  Migration failed - you may need to run it manually")
        else:
            logger.info(f"✅ Database already contains {user_count} users - skipping migration")
    except Exception as e:
        logger.warning(f"⚠️  Could not check migration status: {e}")

# --- Load configurations on startup ---
logger.info("Loading and verifying all configurations...")
google_client_secrets = get_google_client_secrets()
google_user_token = get_google_user_token()
user_config = get_user_config()
verify_all_configs()

# --- Register Blueprints ---
logger.info("Registering API blueprints...")
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# --- Routes ---

@app.route('/', methods=['GET'])
def home():
    """Home endpoint - redirect to admin dashboard"""
    return render_template('admin_dashboard.html'), 200

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    """Admin dashboard"""
    return render_template('admin_dashboard.html'), 200

@app.route('/static/<path:filename>', methods=['GET'])
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "environment": ENVIRONMENT
    }), 200


@app.route('/api/config-status', methods=['GET'])
def config_status():
    """Debugging endpoint to check config loading status"""
    status = {
        "environment": ENVIRONMENT,
        "google_client_secrets": {
            "loaded": bool(google_client_secrets),
            "source": "Base64 Env Var (GOOGLE_CREDS_JSON)" if IS_HEROKU and google_client_secrets else "File (configurations/client_secrets.json)" if google_client_secrets else "Missing"
        },
        "google_user_token": {
            "loaded": bool(google_user_token),
            "source": "Base64 Env Var (GOOGLE_USER_TOKEN_JSON)" if IS_HEROKU and google_user_token else "File (configurations/tokens/jan_avoccado_pareto.json)" if google_user_token else "Missing"
        },
        "user_config": {
            "loaded": bool(user_config),
            "source": "Base64 Env Var (USER_CONFIG_JSON)" if IS_HEROKU and user_config else "File (configurations/users.json)" if user_config else "Missing"
        },
        "database": {
            "initialized": True,
            "type": "SQLite"
        },
        "all_verified": verify_all_configs()
    }
    return jsonify(status), 200


@app.route('/api/chatwoot/webhook', methods=['POST'])
def chatwoot_webhook():
    """Endpoint for Chatwoot webhooks"""
    try:
        data = request.get_json()
        if not data:
            logger.warning("Received empty or non-JSON webhook payload.")
            return jsonify({"status": "error", "message": "Invalid payload"}), 400
        
        # The webhook_handler now accepts the data payload
        response = webhook_handler(data)
        
        # Chatwoot expects a 200 OK response quickly, even if processing is async
        return jsonify({"status": "success", "message": "Webhook received and processing started"}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Error Handlers ---

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }), 500


# --- Main Execution ---

if __name__ == '__main__':
    # Use Heroku's dynamic PORT or default to 8000 for local development
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Admin Dashboard: http://localhost:{port}/admin")
    app.run(host='0.0.0.0', port=port, debug=not IS_HEROKU)
