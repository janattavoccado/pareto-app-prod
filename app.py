"""
Flask Application Entry Point - With Personal Assistant Integration

This file has been updated to ensure all necessary components are imported and
initialized correctly for the Personal Assistant agent to function.

File location: app_new.py
"""

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory

# Database and authentication imports
from pareto_agents.database import get_db_manager
from pareto_agents.auth_routes import auth_bp
from pareto_agents.admin_routes import admin_bp
from pareto_agents.token_routes import token_bp


# Main application components
from pareto_agents.config_loader_v2 import AppConfig
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

# User migration from users.json has been removed.

# --- Load configurations on startup ---
logger.info("Loading and verifying all configurations...")
AppConfig.load_configs()
logger.info("✅ Configurations loaded.")

# --- Register Blueprints ---
logger.info("Registering API blueprints...")
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(token_bp)

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
        "database": {
            "initialized": True,
            "type": "SQLite"
        },
        "configs_loaded": AppConfig.is_loaded()
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
        
        # Chatwoot expects a 200 OK response quickly
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
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Admin Dashboard: http://localhost:{port}/admin")
    app.run(host='0.0.0.0', port=port, debug=not IS_HEROKU)
