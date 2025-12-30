import json
import base64
from typing import Dict, Any

class TokenManager:
    """Handles encoding and decoding of Google user tokens for database storage."""

    @staticmethod
    def encode_token(token_dict: Dict[str, Any]) -> str:
        """Encodes a Google token dictionary to a base64 string."""
        token_json = json.dumps(token_dict)
        token_bytes = token_json.encode('utf-8')
        return base64.b64encode(token_bytes).decode('utf-8')

    @staticmethod
    def decode_token(token_base64: str) -> Dict[str, Any]:
        """Decodes a base64 string back into a Google token dictionary."""
        token_bytes = token_base64.encode('utf-8')
        token_json = base64.b64decode(token_bytes).decode('utf-8')
        return json.loads(token_json)
