"""
Token Manager - Handle Google Token Encoding/Decoding

Provides utilities for:
- Encoding JSON tokens to Base64
- Decoding Base64 tokens to JSON
- Token validation
- Token encryption/decryption

File location: pareto_agents/token_manager.py
"""

import json
import base64
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages encoding and decoding of Google tokens"""
    
    @staticmethod
    def encode_token(token_dict: Dict[str, Any]) -> str:
        """
        Encode a token dictionary to Base64 string
        
        Args:
            token_dict: Dictionary containing token data
            
        Returns:
            Base64 encoded string
            
        Raises:
            ValueError: If token_dict is invalid
        """
        try:
            if not isinstance(token_dict, dict):
                raise ValueError("Token must be a dictionary")
            
            # Convert to JSON string
            json_str = json.dumps(token_dict)
            
            # Encode to Base64
            base64_bytes = base64.b64encode(json_str.encode('utf-8'))
            base64_str = base64_bytes.decode('utf-8')
            
            logger.info("✅ Token encoded to Base64 successfully")
            return base64_str
        
        except Exception as e:
            logger.error(f"❌ Error encoding token: {e}")
            raise ValueError(f"Failed to encode token: {str(e)}")
    
    @staticmethod
    def decode_token(base64_str: str) -> Dict[str, Any]:
        """
        Decode a Base64 string to token dictionary
        
        Args:
            base64_str: Base64 encoded token string
            
        Returns:
            Dictionary containing token data
            
        Raises:
            ValueError: If base64_str is invalid or cannot be decoded
        """
        try:
            if not isinstance(base64_str, str):
                raise ValueError("Base64 token must be a string")
            
            # Decode from Base64
            base64_bytes = base64_str.encode('utf-8')
            json_bytes = base64.b64decode(base64_bytes)
            json_str = json_bytes.decode('utf-8')
            
            # Parse JSON
            token_dict = json.loads(json_str)
            
            logger.info("✅ Token decoded from Base64 successfully")
            return token_dict
        
        except Exception as e:
            logger.error(f"❌ Error decoding token: {e}")
            raise ValueError(f"Failed to decode token: {str(e)}")
    
    @staticmethod
    def encode_from_file(file_path: str) -> str:
        """
        Read a JSON token file and encode to Base64
        
        Args:
            file_path: Path to JSON token file
            
        Returns:
            Base64 encoded string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not valid JSON
        """
        try:
            with open(file_path, 'r') as f:
                token_dict = json.load(f)
            
            return TokenManager.encode_token(token_dict)
        
        except FileNotFoundError:
            logger.error(f"❌ Token file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in token file: {e}")
            raise ValueError(f"Invalid JSON in token file: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error reading token file: {e}")
            raise
    
    @staticmethod
    def decode_to_file(base64_str: str, file_path: str) -> None:
        """
        Decode a Base64 token and write to JSON file
        
        Args:
            base64_str: Base64 encoded token string
            file_path: Path where to write the JSON file
            
        Raises:
            ValueError: If base64_str is invalid
            IOError: If file cannot be written
        """
        try:
            token_dict = TokenManager.decode_token(base64_str)
            
            with open(file_path, 'w') as f:
                json.dump(token_dict, f, indent=2)
            
            logger.info(f"✅ Token written to file: {file_path}")
        
        except Exception as e:
            logger.error(f"❌ Error writing token to file: {e}")
            raise
    
    @staticmethod
    def validate_token(token_dict: Dict[str, Any]) -> bool:
        """
        Validate if a token dictionary has required fields
        
        Args:
            token_dict: Dictionary to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        required_fields = ['type', 'client_id', 'client_secret', 'refresh_token']
        
        if not isinstance(token_dict, dict):
            logger.warning("Token is not a dictionary")
            return False
        
        for field in required_fields:
            if field not in token_dict:
                logger.warning(f"Token missing required field: {field}")
                return False
        
        return True
    
    @staticmethod
    def validate_base64_token(base64_str: str) -> bool:
        """
        Validate if a Base64 string is a valid token
        
        Args:
            base64_str: Base64 encoded token string
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            token_dict = TokenManager.decode_token(base64_str)
            return TokenManager.validate_token(token_dict)
        except Exception as e:
            logger.warning(f"Invalid Base64 token: {e}")
            return False
    
    @staticmethod
    def get_token_info(base64_str: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a token (without sensitive data)
        
        Args:
            base64_str: Base64 encoded token string
            
        Returns:
            Dictionary with token info or None if invalid
        """
        try:
            token_dict = TokenManager.decode_token(base64_str)
            
            # Return non-sensitive info
            return {
                'type': token_dict.get('type'),
                'client_id': token_dict.get('client_id'),
                'has_refresh_token': bool(token_dict.get('refresh_token')),
                'has_access_token': bool(token_dict.get('access_token')),
                'expiry': token_dict.get('expiry'),
            }
        
        except Exception as e:
            logger.warning(f"Error getting token info: {e}")
            return None


# ============================================================================
# Convenience Functions
# ============================================================================

def encode_token(token_dict: Dict[str, Any]) -> str:
    """Encode token dictionary to Base64"""
    return TokenManager.encode_token(token_dict)


def decode_token(base64_str: str) -> Dict[str, Any]:
    """Decode Base64 string to token dictionary"""
    return TokenManager.decode_token(base64_str)


def encode_from_file(file_path: str) -> str:
    """Encode token from JSON file to Base64"""
    return TokenManager.encode_from_file(file_path)


def decode_to_file(base64_str: str, file_path: str) -> None:
    """Decode Base64 token and write to JSON file"""
    return TokenManager.decode_to_file(base64_str, file_path)


def validate_token(token_dict: Dict[str, Any]) -> bool:
    """Validate token dictionary"""
    return TokenManager.validate_token(token_dict)


def validate_base64_token(base64_str: str) -> bool:
    """Validate Base64 encoded token"""
    return TokenManager.validate_base64_token(base64_str)


def get_token_info(base64_str: str) -> Optional[Dict[str, Any]]:
    """Get token information"""
    return TokenManager.get_token_info(base64_str)


if __name__ == '__main__':
    # Test token encoding/decoding
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example token
    example_token = {
        'type': 'authorized_user',
        'client_id': 'example.apps.googleusercontent.com',
        'client_secret': 'example_secret',
        'refresh_token': 'example_refresh_token',
        'access_token': 'example_access_token',
        'expiry': '2025-12-27T10:00:00Z'
    }
    
    # Encode
    encoded = encode_token(example_token)
    logger.info(f"Encoded token: {encoded[:50]}...")
    
    # Decode
    decoded = decode_token(encoded)
    logger.info(f"Decoded token type: {decoded.get('type')}")
    
    # Validate
    is_valid = validate_base64_token(encoded)
    logger.info(f"Token is valid: {is_valid}")
    
    # Get info
    info = get_token_info(encoded)
    logger.info(f"Token info: {info}")
