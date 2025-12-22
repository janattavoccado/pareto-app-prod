import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Corrected Import: Use absolute import from the package
from pareto_agents.config_loader import get_google_credentials, get_user_config, verify_all_configs
from pareto_agents.chatwoot_webhook import webhook_handler

# Load environment variables from .env file (for local development)
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration Verification ---
# This will log the status of all required configurations on startup
verify_all_configs()

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Routes ---

@app.route('/')
def home():
    """Simple home route for health check."""
    return jsonify({"status": "ok", "message": "Valhalla Flask App is running"})

@app.route('/health')
def health_check():
    """
    Detailed health check endpoint.
    Verifies the status of all critical configurations.
    """
    # Re-verify configs to ensure they are still available
    all_good = verify_all_configs()
    
    # Check environment
    environment = os.getenv('FLASK_ENV', 'development')
    
    return jsonify({
        "status": "healthy" if all_good else "unhealthy",
        "service": "Valhalla Flask App",
        "environment": environment,
        "configs": {
            "google_credentials": bool(get_google_credentials()),
            "user_config": bool(get_user_config()),
            "openai_api_key": bool(os.getenv('OPENAI_API_KEY')),
            "chatwoot_credentials": bool(os.getenv('CHATWOOT_ACCOUNT_ID') and os.getenv('CHATWOOT_API_KEY'))
        }
    }), 200 if all_good else 503

@app.route('/api/chatwoot/webhook', methods=['POST'])
def chatwoot_webhook():
    """
    Handles incoming webhook events from Chatwoot.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        response = webhook_handler(data)
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# --- Main Execution ---

if __name__ == '__main__':
    # Heroku uses the PORT environment variable
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)
