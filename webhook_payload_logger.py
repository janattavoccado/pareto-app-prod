"""
Webhook Payload Logger - Debug Script
Logs complete webhook payloads to analyze message structure
Especially useful for audio, image, and other media messages

Usage:
1. Replace the webhook handler in chatwoot_webhook.py temporarily
2. Send messages (text, audio, image, etc.)
3. Check logs to see full payload structure
4. Use the structure to implement proper handling
"""

import logging
import json
from flask import Blueprint, request, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
debug_bp = Blueprint('debug', __name__, url_prefix='/api/debug')


@debug_bp.route('/webhook', methods=['POST'])
def webhook_payload_logger():
    """
    Log complete webhook payload for debugging
    """
    try:
        # Get raw payload
        payload = request.get_json()
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log separator
        logger.info("=" * 80)
        logger.info(f"WEBHOOK PAYLOAD RECEIVED - {timestamp}")
        logger.info("=" * 80)
        
        # Log full payload as formatted JSON
        logger.info("FULL PAYLOAD:")
        logger.info(json.dumps(payload, indent=2))
        
        # Extract and log key fields
        logger.info("\n" + "=" * 80)
        logger.info("KEY FIELDS EXTRACTED:")
        logger.info("=" * 80)
        
        # Message metadata
        message_id = payload.get('id')
        message_type = payload.get('message_type')
        content = payload.get('content', '')
        content_type = payload.get('content_type')
        
        logger.info(f"Message ID: {message_id}")
        logger.info(f"Message Type: {message_type}")
        logger.info(f"Content Type: {content_type}")
        logger.info(f"Content Length: {len(content) if content else 0}")
        logger.info(f"Content Preview: {content[:100] if content else 'EMPTY'}")
        
        # Conversation info
        conversation = payload.get('conversation', {})
        logger.info(f"\nConversation ID: {conversation.get('id')}")
        logger.info(f"Conversation Status: {conversation.get('status')}")
        
        # Sender info
        sender = payload.get('sender', {})
        logger.info(f"\nSender Name: {sender.get('name')}")
        logger.info(f"Sender Phone: {sender.get('phone_number')}")
        logger.info(f"Sender Email: {sender.get('email')}")
        
        # Attachments/Media
        attachments = payload.get('attachments', [])
        logger.info(f"\nAttachments Count: {len(attachments)}")
        if attachments:
            for i, attachment in enumerate(attachments):
                logger.info(f"\n  Attachment {i+1}:")
                logger.info(f"    Type: {attachment.get('file_type')}")
                logger.info(f"    URL: {attachment.get('file_url')}")
                logger.info(f"    Thumb URL: {attachment.get('thumb_url')}")
                logger.info(f"    Size: {attachment.get('size')}")
                logger.info(f"    Full: {json.dumps(attachment, indent=6)}")
        
        # Media
        media = payload.get('media', {})
        if media:
            logger.info(f"\nMedia:")
            logger.info(f"  Type: {media.get('type')}")
            logger.info(f"  URL: {media.get('url')}")
            logger.info(f"  Full: {json.dumps(media, indent=4)}")
        
        # Additional fields
        logger.info(f"\nAdditional Fields:")
        logger.info(f"  Source ID: {payload.get('source_id')}")
        logger.info(f"  Created At: {payload.get('created_at')}")
        logger.info(f"  Inbox ID: {payload.get('inbox_id')}")
        logger.info(f"  Account ID: {payload.get('account_id')}")
        
        # Log all keys in payload
        logger.info(f"\nAll Payload Keys:")
        for key in sorted(payload.keys()):
            value = payload[key]
            if isinstance(value, (dict, list)):
                logger.info(f"  {key}: <{type(value).__name__}>")
            else:
                logger.info(f"  {key}: {value}")
        
        logger.info("=" * 80)
        logger.info("END OF PAYLOAD")
        logger.info("=" * 80 + "\n")
        
        # Return success
        return jsonify({
            "status": "logged",
            "message_id": message_id,
            "message_type": message_type,
            "has_content": bool(content),
            "has_attachments": len(attachments) > 0,
            "has_media": bool(media)
        }), 200
    
    except Exception as e:
        logger.error(f"Error logging webhook: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@debug_bp.route('/test-payload', methods=['POST'])
def test_payload():
    """
    Test endpoint to send sample payloads
    Useful for testing without actual WhatsApp messages
    """
    try:
        payload = request.get_json()
        
        logger.info("=" * 80)
        logger.info("TEST PAYLOAD RECEIVED")
        logger.info("=" * 80)
        logger.info(json.dumps(payload, indent=2))
        logger.info("=" * 80)
        
        return jsonify({"status": "test_logged"}), 200
    
    except Exception as e:
        logger.error(f"Error in test payload: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Sample payloads for reference
SAMPLE_TEXT_PAYLOAD = {
    "id": 123,
    "message_type": "incoming",
    "content": "Hello, this is a text message",
    "content_type": "text",
    "conversation": {"id": 1},
    "sender": {
        "name": "John Doe",
        "phone_number": "+1234567890",
        "email": "john@example.com"
    },
    "attachments": [],
    "created_at": "2025-12-17T17:04:33Z"
}

SAMPLE_AUDIO_PAYLOAD = {
    "id": 124,
    "message_type": "incoming",
    "content": "",  # Audio has no text content
    "content_type": "audio",
    "conversation": {"id": 1},
    "sender": {
        "name": "John Doe",
        "phone_number": "+1234567890",
        "email": "john@example.com"
    },
    "attachments": [
        {
            "file_type": "audio",
            "file_url": "https://example.com/audio/message.mp3",
            "thumb_url": None,
            "size": 45678
        }
    ],
    "media": {
        "type": "audio",
        "url": "https://example.com/audio/message.mp3"
    },
    "created_at": "2025-12-17T17:04:33Z"
}

SAMPLE_IMAGE_PAYLOAD = {
    "id": 125,
    "message_type": "incoming",
    "content": "Check out this image",
    "content_type": "image",
    "conversation": {"id": 1},
    "sender": {
        "name": "John Doe",
        "phone_number": "+1234567890",
        "email": "john@example.com"
    },
    "attachments": [
        {
            "file_type": "image",
            "file_url": "https://example.com/images/photo.jpg",
            "thumb_url": "https://example.com/images/photo_thumb.jpg",
            "size": 123456
        }
    ],
    "media": {
        "type": "image",
        "url": "https://example.com/images/photo.jpg"
    },
    "created_at": "2025-12-17T17:04:33Z"
}


@debug_bp.route('/sample-text', methods=['POST'])
def send_sample_text():
    """Send sample text payload for testing"""
    logger.info("Sending sample TEXT payload...")
    logger.info(json.dumps(SAMPLE_TEXT_PAYLOAD, indent=2))
    return jsonify(SAMPLE_TEXT_PAYLOAD), 200


@debug_bp.route('/sample-audio', methods=['POST'])
def send_sample_audio():
    """Send sample audio payload for testing"""
    logger.info("Sending sample AUDIO payload...")
    logger.info(json.dumps(SAMPLE_AUDIO_PAYLOAD, indent=2))
    return jsonify(SAMPLE_AUDIO_PAYLOAD), 200


@debug_bp.route('/sample-image', methods=['POST'])
def send_sample_image():
    """Send sample image payload for testing"""
    logger.info("Sending sample IMAGE payload...")
    logger.info(json.dumps(SAMPLE_IMAGE_PAYLOAD, indent=2))
    return jsonify(SAMPLE_IMAGE_PAYLOAD), 200


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Webhook Payload Logger Ready")
    logger.info("Endpoints:")
    logger.info("  POST /api/debug/webhook - Log incoming webhook")
    logger.info("  POST /api/debug/test-payload - Test custom payload")
    logger.info("  POST /api/debug/sample-text - Get sample text payload")
    logger.info("  POST /api/debug/sample-audio - Get sample audio payload")
    logger.info("  POST /api/debug/sample-image - Get sample image payload")
