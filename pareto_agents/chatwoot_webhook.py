"""
Chatwoot Webhook Handler
Handles incoming messages and routes to appropriate action executors
Preserves mail me functionality and calendar support
BOTH TEXT AND AUDIO MESSAGE SUPPORT

File location: pareto_agents/chatwoot_webhook.py
"""

import logging
from flask import Blueprint, request, jsonify

from .user_manager import get_user_manager
from .chatwoot_client import ChatwootClient

logger = logging.getLogger(__name__)

# Create blueprint
chatwoot_bp = Blueprint('chatwoot', __name__, url_prefix='/api/chatwoot')


# ============================================================================
# Webhook Handler
# ============================================================================

def webhook_handler(payload):
    """
    Main Chatwoot webhook handler
    Receives messages from Chatwoot and processes them through agents
    """
    try:
        # Lazy import to avoid circular dependency
        from .agents import process_message_sync

        # Get payload
        # NOTE: The payload is now passed as an argument from app.py
        # payload = request.get_json() # REMOVED

        if not payload:
            logger.warning("Empty webhook payload")
            return {"error": "Empty payload"} # Return dict instead of jsonify

        logger.debug(f"Webhook payload received")

        # Extract message data
        message_id = payload.get('id')
        message_type = payload.get('message_type')
        content = payload.get('content', '')
        conversation_id = payload.get('conversation', {}).get('id')
        sender = payload.get('sender', {})
        phone_number = sender.get('phone_number')

        logger.info(
            f"Chatwoot webhook event received: message_created | "
            f"ID={message_id}, Conv={conversation_id}, Type={message_type}, Phone={phone_number}"
        )

        # Skip outgoing messages
        if message_type == 'outgoing':
            logger.info(f"Skipping outgoing message {message_id}")
            return {"status": "skipped"} # Return dict instead of jsonify

        # Check for audio message
        attachments = payload.get('attachments', [])
        is_audio = any(att.get('file_type') == 'audio' for att in attachments)

        # Validate required fields (audio messages don't have content)
        if not is_audio and not all([phone_number, content, conversation_id]):
            logger.warning(
                f"Missing required fields | Phone: {phone_number}, Content: {bool(content)}, Conv: {conversation_id}"
            )
            return {"error": "Missing required fields"} # Return dict instead of jsonify

        if not all([phone_number, conversation_id]):
            logger.warning(
                f"Missing required fields | Phone: {phone_number}, Conv: {conversation_id}"
            )
            return {"error": "Missing required fields"} # Return dict instead of jsonify

        logger.info(
            f"Processing message | ID: {message_id} | Conversation: {conversation_id} | "
            f"Phone: {phone_number} | Content: {content[:50] if content else 'AUDIO'}..."
        )

        # Get user manager and check authorization
        user_manager = get_user_manager()
        user_data = user_manager.get_user_by_phone(phone_number)

        if not user_data or not user_data.get('enabled'):
            logger.warning(f"User not authorized: {phone_number}")

            # Send access denied message
            chatwoot_client = ChatwootClient()
            chatwoot_client.send_message(
                conversation_id=conversation_id,
                message_text="You do not have access to the service, please contact AVOCCADO Tech sales team for assistance.",
                private=False
            )

            return {"status": "unauthorized"} # Return dict instead of jsonify

        # Log authorized user
        user_name = f"{user_data.get('first_name')} {user_data.get('last_name')}"
        logger.info(f"Processing message from authorized user: {user_name} ({phone_number})")

        # Handle audio messages
        message_to_process = content
        if is_audio:
            logger.info(f"Starting audio message handling for {phone_number}")
            from .audio_transcriber import AudioTranscriber

            audio_url = None
            for attachment in attachments:
                if attachment.get('file_type') == 'audio':
                    audio_url = attachment.get('data_url')
                    break

            if not audio_url:
                logger.error("Audio attachment found but no URL")
                return {"error": "Audio URL not found"} # Return dict instead of jsonify

            logger.info(f"Transcribing audio message...")
            transcriber = AudioTranscriber()
            transcribed_text = transcriber.transcribe_from_url(audio_url)

            if not transcribed_text:
                logger.error("Audio transcription failed")
                chatwoot_client = ChatwootClient()
                chatwoot_client.send_message(
                    conversation_id=conversation_id,
                    message_text="Failed to transcribe audio message",
                    private=False
                )
                return {"status": "transcription_failed"} # Return dict instead of jsonify

            logger.info(f"Audio transcribed successfully: {transcribed_text[:100]}...")
            message_to_process = transcribed_text

        # Process message through agents
        agent_result = process_message_sync(
            message=message_to_process,
            phone_number=phone_number,
            user_data=user_data,
        )

        if not agent_result:
            logger.error("Agent processing returned None")
            return {"error": "Agent processing failed"} # Return dict instead of jsonify

        # Handle mail me command
        if agent_result.get('is_mail_me'):
            logger.info("Processing mail me command")

            mail_me_request = agent_result.get('mail_me_request')
            if not mail_me_request:
                logger.error("Mail me request is None")
                return {"error": "Mail me request failed"} # Return dict instead of jsonify

            try:
                # Execute mail me action
                from .google_email_client import GoogleEmailClient

                token_path = user_data.get('google_token_path')
                email_client = GoogleEmailClient(token_path)

                success = email_client.send_email(
                    to=user_data.get('email'),
                    subject=mail_me_request.subject,
                    body=mail_me_request.body
                )

                if success:
                    response_msg = agent_result.get('agent_response', 'Email sent successfully')
                    logger.info(f"Email sent successfully to {user_data.get('email')}")
                else:
                    response_msg = "Failed to send email"
                    logger.error("Email sending failed")

                # Send response to Chatwoot
                chatwoot_client = ChatwootClient()
                chatwoot_client.send_message(
                    conversation_id=conversation_id,
                    message_text=response_msg,
                    private=False
                )

                logger.info(f"Mail me command executed and response sent to Chatwoot")
                return {"status": "success", "action": "mail_me"} # Return dict instead of jsonify

            except Exception as e:
                error_msg = f"Error sending email: {str(e)}"
                logger.error(error_msg, exc_info=True)
                chatwoot_client = ChatwootClient()
                chatwoot_client.send_message(
                    conversation_id=conversation_id,
                    message_text=error_msg,
                    private=False
                )
                return {"status": "error", "action": "mail_me"} # Return dict instead of jsonify

        # Handle regular agent response
        logger.info("Processing regular agent response")

        agent_response = agent_result.get('agent_response', '')

        if not agent_response:
            logger.warning("No agent response generated")
            return {"error": "No response generated"} # Return dict instead of jsonify

        logger.info(f"Agent response ready | Action: {agent_result.get('action_type')} | User: {user_name}")

        # Check if response contains calendar or email action
        action_type = _detect_action_type(agent_response)
        logger.info(f"Detected action type: {action_type}")

        # Execute action if needed
        if action_type == 'calendar':
            logger.info("Executing calendar action")

            # Lazy import for calendar executor
            from .calendar_action_executor import CalendarActionExecutor

            calendar_executor = CalendarActionExecutor(phone_number)
            action_result = calendar_executor.execute_action(agent_result.get('raw_result'))

            formatted_response = _format_action_response(action_result, user_data)

            logger.info(f"Action execution result: {action_result.action}")

        elif action_type == 'email':
            logger.info("Executing email action")

            # Lazy import for email executor
            from .email_action_executor import EmailActionExecutor

            email_executor = EmailActionExecutor(phone_number)
            action_result = email_executor.execute_action(agent_result.get('raw_result'))

            formatted_response = _format_action_response(action_result, user_data)

            logger.info(f"Action execution result: {action_result.action}")

        else:
            # No specific action, just send agent response
            formatted_response = agent_response

        # Send response to Chatwoot
        chatwoot_client = ChatwootClient()

        chatwoot_client.send_message(
            conversation_id=conversation_id,
            message_text=formatted_response,
            private=False
        )

        logger.info(f"Response sent to Chatwoot | Conversation: {conversation_id} | Message ID: {message_id}")

        return {"status": "success"} # Return dict instead of jsonify

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"error": str(e)} # Return dict instead of jsonify

# ============================================================================
# Helper Functions
# ============================================================================

def _detect_action_type(response_text: str) -> str:
    """
    Detect if the response contains calendar or email action
    """
    response_lower = response_text.lower()

    if any(word in response_lower for word in ['calendar', 'event', 'meeting', 'scheduled', 'appointment']):
        return 'calendar'
    elif any(word in response_lower for word in ['email', 'mail', 'sent', 'send']):
        return 'email'

    return 'none'


def _format_action_response(action_result, user_data: dict) -> str:
    """
    Format action result response for Chatwoot
    """
    if hasattr(action_result, 'response'):
        return action_result.response
    elif isinstance(action_result, dict) and 'response' in action_result:
        return action_result['response']

    return "Action completed successfully"


# ============================================================================
# Health Check Endpoint
# ============================================================================

@chatwoot_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Lazy import to avoid circular dependency
        from .timezone_service import TimezoneService

        timezone_service = TimezoneService()
        current_time = timezone_service.get_current_time_cet()

        return jsonify({
            "status": "healthy",
            "current_time_cet": current_time.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_action_type(response_text: str) -> str:
    """
    Detect if the response contains calendar or email action
    """
    response_lower = response_text.lower()

    if any(word in response_lower for word in ['calendar', 'event', 'meeting', 'scheduled', 'appointment']):
        return 'calendar'
    elif any(word in response_lower for word in ['email', 'mail', 'sent', 'send']):
        return 'email'

    return 'none'


def _format_action_response(action_result, user_data: dict) -> str:
    """
    Format action result response for Chatwoot
    """
    if hasattr(action_result, 'response'):
        return action_result.response
    elif isinstance(action_result, dict) and 'response' in action_result:
        return action_result['response']

    return "Action completed successfully"


# ============================================================================
# Health Check Endpoint
# ============================================================================

@chatwoot_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Lazy import to avoid circular dependency
        from .timezone_service import TimezoneService

        timezone_service = TimezoneService()
        current_time = timezone_service.get_current_time_cet()

        return jsonify({
            "status": "healthy",
            "current_time_cet": current_time.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500
