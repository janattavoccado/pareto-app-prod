from flask import Blueprint, request, jsonify
from .database import get_db_session, User
from .google_token_manager import TokenManager
import json

token_bp = Blueprint("tokens", __name__, url_prefix="/api/tokens")

@token_bp.route("/users/<int:user_id>/get", methods=["GET"])
def get_user_token(user_id):
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if not user.google_token_base64:
            return jsonify({"success": True, "has_token": False}), 200

        token_info = TokenManager.get_token_info(user.google_token_base64)
        return jsonify({"success": True, "has_token": True, "token_info": token_info}), 200
    finally:
        session.close()

@token_bp.route("/users/<int:user_id>/set", methods=["POST"])
def set_user_token(user_id):
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        if "file" not in request.files:
            if request.is_json and "token" in request.json and request.json["token"] is None:
                user.google_token_base64 = None
                session.commit()
                return jsonify({"success": True, "message": "Token deleted successfully"}), 200
            return jsonify({"success": False, "message": "No file part"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No selected file"}), 400
        
        if file:
            try:
                token_data = json.load(file)
                if not TokenManager.validate_token(token_data):
                    return jsonify({"success": False, "message": "Invalid token format"}), 400
                user.google_token_base64 = TokenManager.encode_token(token_data)
                session.commit()
                return jsonify({"success": True, "message": "Token updated successfully"}), 200
            except json.JSONDecodeError:
                return jsonify({"success": False, "message": "Invalid JSON file"}), 400
    finally:
        session.close()
