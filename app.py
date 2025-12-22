"""
Updated Flask Application with Pareto Agents Integration
"""

import os
import logging
from flask import Flask
from dotenv import load_dotenv
from pareto_agents.chatwoot_webhook import chatwoot_bp

from webhook_payload_logger import debug_bp



# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Register debug blueprint
app.register_blueprint(debug_bp)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Register the Chatwoot webhook blueprint
app.register_blueprint(chatwoot_bp)

# Your existing routes
@app.route("/")
def index():
    return {"message": "Valhalla API Server"}, 200

@app.route("/health")
def health():
    return {
        "status": "healthy",
        "service": "Valhalla Flask App"
    }, 200

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logger.info(f"Starting Valhalla Flask App on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
