"""
Token Management Routes

Provides Flask endpoints for managing Google tokens:
- Upload/set token for user
- Download/get token for user
- Delete token
- Validate token
- Get token info

File location: pareto_agents/token_routes.py
"""

import logging
import json
from flask import Blueprint, request, jsonify

from .auth import require_auth
from .database import get_db_session, User
from .token_manager import TokenManager
from .user_manager_db_v2 import get_user_manager_db_v2

logger = logging.getLogger(__name__)

# Create blueprint
token_bp = Blueprint('tokens', __name__, url_prefix='/api/tokens')


# ============================================================================
# Token Management Routes
# ============================================================================

@token_bp.route('/users/<int:user_id>/set', methods=['POST'])
@require_auth
def set_user_token(user_id):
    """
    Set/upload Google token for a user
    
    Request body:
    {
        "token_json": {...}  // JSON token object
    }
    
    Or multipart form with file upload:
    - file: JSON token file
    
    Response:
    {
        "success": true,
        "message": "Token set successfully",
        "token_info": {...}
    }
    """
    try:
        admin_info = request.admin_info
        
        # Get user
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            token_dict = None
            
            # Check if JSON body
            if request.is_json:
                data = request.get_json()
                token_dict = data.get('token_json')
            
            # Check if file upload
            elif 'file' in request.files:
                file = request.files['file']
                try:
                    token_dict = json.load(file)
                except json.JSONDecodeError:
                    logger.warning("❌ Invalid JSON in uploaded file")
                    return jsonify({'success': False, 'message': 'Invalid JSON in file'}), 400
            
            if not token_dict:
                logger.warning("❌ No token provided")
                return jsonify({'success': False, 'message': 'Token JSON is required'}), 400
            
            # Validate token
            token_manager = TokenManager()
            if not token_manager.validate_token(token_dict):
                logger.warning("❌ Invalid token format")
                return jsonify({'success': False, 'message': 'Invalid token format'}), 400
            
            # Encode and store token
            base64_token = token_manager.encode_token(token_dict)
            user.google_token_base64 = base64_token
            session.commit()
            
            # Get token info
            token_info = token_manager.get_token_info(base64_token)
            
            logger.info(f"✅ Set Google token for user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'message': 'Token set successfully',
                'token_info': token_info
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Error setting token: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@token_bp.route('/users/<int:user_id>/get', methods=['GET'])
@require_auth
def get_user_token(user_id):
    """
    Get token info for a user (does not return sensitive data)
    
    Response:
    {
        "success": true,
        "has_token": true,
        "token_info": {
            "type": "authorized_user",
            "client_id": "...",
            "has_refresh_token": true,
            "has_access_token": true,
            "expiry": "2025-12-27T10:00:00Z"
        }
    }
    """
    try:
        admin_info = request.admin_info
        
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            if not user.google_token_base64:
                logger.info(f"ℹ️  User has no token: {user_id}")
                return jsonify({
                    'success': True,
                    'has_token': False,
                    'message': 'User has no token configured'
                }), 200
            
            # Get token info
            token_manager = TokenManager()
            token_info = token_manager.get_token_info(user.google_token_base64)
            
            logger.info(f"✅ Retrieved token info for user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'has_token': True,
                'token_info': token_info
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Error getting token: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@token_bp.route('/users/<int:user_id>/delete', methods=['DELETE'])
@require_auth
def delete_user_token(user_id):
    """
    Delete Google token for a user
    
    Response:
    {
        "success": true,
        "message": "Token deleted successfully"
    }
    """
    try:
        admin_info = request.admin_info
        
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            user.google_token_base64 = None
            session.commit()
            
            logger.info(f"✅ Deleted Google token for user: {user.full_name}")
            
            return jsonify({
                'success': True,
                'message': 'Token deleted successfully'
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Error deleting token: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@token_bp.route('/validate', methods=['POST'])
@require_auth
def validate_token():
    """
    Validate a token
    
    Request body:
    {
        "token_json": {...}
    }
    
    Response:
    {
        "success": true,
        "is_valid": true,
        "message": "Token is valid"
    }
    """
    try:
        admin_info = request.admin_info
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Request body is required'}), 400
        
        token_dict = data.get('token_json')
        
        if not token_dict:
            return jsonify({'success': False, 'message': 'Token JSON is required'}), 400
        
        token_manager = TokenManager()
        is_valid = token_manager.validate_token(token_dict)
        
        if is_valid:
            logger.info("✅ Token validation successful")
            return jsonify({
                'success': True,
                'is_valid': True,
                'message': 'Token is valid'
            }), 200
        else:
            logger.warning("❌ Token validation failed")
            return jsonify({
                'success': True,
                'is_valid': False,
                'message': 'Token is invalid or missing required fields'
            }), 200
    
    except Exception as e:
        logger.error(f"❌ Error validating token: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@token_bp.route('/health', methods=['GET'])
def token_health():
    """
    Health check for token service
    
    Response:
    {
        "status": "healthy",
        "service": "Token Management API"
    }
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Token Management API'
    }), 200


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Token routes module loaded successfully")
