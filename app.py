"""
Flask Application Entry Point

This file has been updated to:
1. Use the correct import names from the final config_loader.py.
2. Handle Heroku's dynamic PORT environment variable.
3. Include a /config-status endpoint for debugging.
4. Register all blueprints for admin, CRM, and user authentication.
5. Serve static files and templates for dashboards.
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory

# Corrected imports from the final config_loader.py
from pareto_agents.config_loader import (
    get_google_client_secrets,
    get_google_user_token,
    get_user_config,
    verify_all_configs
)
from pareto_agents.chatwoot_webhook import webhook_handler

# Import blueprints
from pareto_agents.auth_routes import auth_bp
from pareto_agents.admin_routes import admin_bp
from pareto_agents.crm_routes import crm_admin_bp, crm_user_bp
from pareto_agents.user_auth import user_auth_bp

# --- Configuration ---
# Determine environment
IS_HEROKU = 'DYNO' in os.environ
ENVIRONMENT = 'Heroku Production' if IS_HEROKU else 'Local Development'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Starting Flask app in {ENVIRONMENT} environment.")

# --- App Initialization ---
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(crm_admin_bp)
app.register_blueprint(crm_user_bp)
app.register_blueprint(user_auth_bp)

logger.info("Registered all Flask blueprints")

# Load configurations on startup
logger.info("Loading and verifying all configurations...")
google_client_secrets = get_google_client_secrets()
google_user_token = get_google_user_token()
user_config = get_user_config()
verify_all_configs()

# --- Routes ---

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "environment": ENVIRONMENT}), 200

@app.route('/config-status', methods=['GET'])
def config_status():
    """Debugging endpoint to check config loading status."""
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
        "all_verified": verify_all_configs()
    }
    return jsonify(status), 200

@app.route('/api/chatwoot/webhook', methods=['POST'])
def chatwoot_webhook():
    """Endpoint for Chatwoot webhooks."""
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


# --- Dashboard Routes ---

@app.route('/admin')
@app.route('/admin/')
def admin_dashboard():
    """Serve the admin dashboard."""
    return render_template('admin_dashboard.html')

@app.route('/crm')
@app.route('/crm/')
def user_crm_portal():
    """Serve the user CRM portal."""
    return render_template('user_crm_portal.html')


# --- Static Files ---

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


# --- Main Execution ---

if __name__ == '__main__':
    # Use Heroku's dynamic PORT or default to 8000 for local development
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=not IS_HEROKU)
