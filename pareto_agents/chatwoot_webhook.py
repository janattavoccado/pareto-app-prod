"""
Chatwoot Webhook Handler -

Handles incoming messages from Chatwoot, authorizes users, and routes messages
to the appropriate agent handler (MailMe, Calendar, Email, or Personal Assistant).

File location: pareto_agents/chatwoot_webhook.py
"""

import logging
from flask import Blueprint, request, jsonify

from .user_manager_db_v2 import get_user_manager
from .chatwoot_client import ChatwootClient
from .config_loader_v2 import AppConfig

# Lazy import agents to avoid circular dependencies
from . import agents

logger = logging.getLogger(__name__)

# Create blueprint
chatwoot_bp = Blueprint("chatwoot", __name__, url_prefix="/api/chatwoot")


# ============================================================================
# Response Formatting
# ============================================================================

def _format_action_response(action_result, user_data) -> str:
    """
    Formats the response from an action executor.
    """
    if not hasattr(action_result, "response") or not action_result.response:
        return "Action completed, but no specific response was generated."
    return action_result.response


# ============================================================================
# Webhook Handler
# ============================================================================

def webhook_handler(payload):
    """
    Main Chatwoot webhook handler.
    """
    conversation_id = None

    try:
        if not payload:
            logger.warning("Empty webhook payload received.")
            return {"error": "Empty payload"}

        # Extract essential data from payload
        message_type = payload.get("message_type")
        conversation_id = payload.get("conversation", {}).get("id")
        phone_number = payload.get("sender", {}).get("phone_number")

        # Skip outgoing messages
        if message_type == "outgoing":
            return {"status": "skipped_outgoing"}

        if not all([phone_number, conversation_id]):
            logger.warning(f"Webhook missing phone_number or conversation_id.")
            return {"error": "Missing required fields"}

        # --- User Authorization ---
        user_manager = get_user_manager()
        user_data = user_manager.get_user_by_phone(phone_number)

        if not user_data or not user_data.get("is_enabled"):
            logger.warning(f"Unauthorized access attempt from {phone_number}")
            ChatwootClient().send_message(
                conversation_id=conversation_id,
                message_text="You do not have access to this service. Please contact support."
            )
            return {"status": "unauthorized"}

        user_name = f"{user_data.get('first_name')} {user_data.get('last_name')}"
        logger.info(f"Processing message from authorized user: {user_name} ({phone_number})")

        # --- Message Content Processing ---
        content = payload.get("content", "")
        attachments = payload.get("attachments", [])
        is_audio = any(att.get("file_type") == "audio" for att in attachments)

        message_to_process = content
        
        # Handle audio messages - transcribe using OpenAI Whisper
        if is_audio:
            logger.info("Audio message detected, starting transcription...")
            try:
                from .audio_transcriber import AudioTranscriber, extract_audio_from_payload
                
                # Extract audio URL from payload
                audio_url = extract_audio_from_payload(payload)
                
                if audio_url:
                    # Transcribe the audio
                    transcriber = AudioTranscriber()
                    transcribed_text = transcriber.transcribe_from_url(audio_url)
                    
                    if transcribed_text:
                        logger.info(f"Audio transcribed successfully: {transcribed_text[:100]}...")
                        message_to_process = transcribed_text
                    else:
                        logger.warning("Audio transcription returned empty text")
                        ChatwootClient().send_message(
                            conversation_id=conversation_id,
                            message_text="❌ I couldn't understand the audio message. Please try again or send a text message."
                        )
                        return {"status": "transcription_empty"}
                else:
                    logger.warning("Could not extract audio URL from payload")
                    ChatwootClient().send_message(
                        conversation_id=conversation_id,
                        message_text="❌ I couldn't process the audio message. Please try again."
                    )
                    return {"status": "audio_url_missing"}
                    
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}", exc_info=True)
                ChatwootClient().send_message(
                    conversation_id=conversation_id,
                    message_text="❌ I had trouble processing your voice message. Please try again or send a text message."
                )
                return {"status": "transcription_error", "error": str(e)}

        if not message_to_process:
            logger.warning("No content to process after handling attachments.")
            return {"status": "no_content"}

        # --- Agent Processing ---
        agent_result = agents.process_message_sync(
            message=message_to_process,
            phone_number=phone_number,
            user_data=user_data,
        )

        if not agent_result:
            logger.error("Agent processing returned a null result.")
            return {"error": "Agent processing failed"}

        # --- Response Handling ---
        action_type = agent_result.get("action_type", "none")
        agent_response = agent_result.get("agent_response", "")

        logger.info(f"Agent action type: {action_type}")

        # Handle MailMe action
        if action_type == "mail_me" and agent_result.get("mail_me_request"):
            logger.info("Processing MailMe action.")
            try:
                from .mail_me_handler import MailMeHandler
                mail_me_request = agent_result.get("mail_me_request")

                # Send the email
                success = MailMeHandler.send_mail_me_email(
                    phone_number=phone_number,
                    mail_me_request=mail_me_request
                )

                if success:
                    final_response = agent_response
                else:
                    final_response = "❌ Failed to send the email. Please try again."

            except Exception as e:
                logger.error(f"MailMe action failed: {e}", exc_info=True)
                final_response = f"❌ Error sending email: {str(e)}"

        # Handle Calendar action (booking, creating, updating, deleting)
        elif action_type == "calendar":
            logger.info("Processing Calendar action.")
            try:
                from .calendar_action_executor import CalendarActionExecutor
                executor = CalendarActionExecutor(phone_number)
                action_result_obj = executor.execute_action(agent_result.get("raw_result"))

                if hasattr(action_result_obj, "response") and action_result_obj.response:
                    final_response = action_result_obj.response
                else:
                    final_response = agent_response

            except Exception as e:
                logger.error(f"Calendar action failed: {e}", exc_info=True)
                final_response = agent_response  # Fall back to agent response

        # Handle Email action (sending, composing)
        elif action_type == "email":
            logger.info("Processing Email action.")
            try:
                from .email_action_executor import EmailActionExecutor
                executor = EmailActionExecutor(phone_number)
                action_result_obj = executor.execute_action(agent_result.get("raw_result"))

                if hasattr(action_result_obj, "response") and action_result_obj.response:
                    final_response = action_result_obj.response
                else:
                    final_response = agent_response

            except Exception as e:
                logger.error(f"Email action failed: {e}", exc_info=True)
                final_response = agent_response  # Fall back to agent response

        # Handle Personal Assistant response (queries, summaries, greetings)
        elif action_type == "personal_assistant":
            logger.info("Processing Personal Assistant response.")
            # For queries and summaries, we may need to execute calendar/email reads
            try:
                # Check for simple questions first (date, time, etc.) - use agent response directly
                if _is_simple_question(message_to_process):
                    logger.info("Simple question detected - using agent response directly.")
                    final_response = agent_response
                
                # Check if the response indicates calendar information is needed
                elif _needs_calendar_data(message_to_process):
                    from .calendar_action_executor import CalendarActionExecutor
                    executor = CalendarActionExecutor(phone_number)
                    action_result_obj = executor.execute_action(agent_result.get("raw_result"))

                    if hasattr(action_result_obj, "response") and action_result_obj.response:
                        final_response = action_result_obj.response
                    else:
                        final_response = agent_response

                # Check if the response indicates email information is needed
                elif _needs_email_data(message_to_process):
                    from .email_action_executor import EmailActionExecutor
                    executor = EmailActionExecutor(phone_number)
                    action_result_obj = executor.execute_action(agent_result.get("raw_result"))

                    if hasattr(action_result_obj, "response") and action_result_obj.response:
                        final_response = action_result_obj.response
                    else:
                        final_response = agent_response
                else:
                    # General conversation or greeting
                    final_response = agent_response

            except Exception as e:
                logger.error(f"Personal Assistant action failed: {e}", exc_info=True)
                final_response = agent_response  # Fall back to agent response

        else:
            # Default: use agent response directly
            final_response = agent_response

        # Send the final response to Chatwoot
        if final_response:
            ChatwootClient().send_message(
                conversation_id=conversation_id, message_text=final_response
            )
            logger.info(f"Final response sent to Chatwoot for conversation {conversation_id}.")
            
            # Check for additional messages (used by help command for long content)
            additional_messages = agent_result.get("additional_messages", [])
            if additional_messages:
                import time
                logger.info(f"Sending {len(additional_messages)} additional messages for {action_type}")
                for i, extra_msg in enumerate(additional_messages):
                    time.sleep(0.5)  # Small delay between messages to maintain order
                    ChatwootClient().send_message(
                        conversation_id=conversation_id, message_text=extra_msg
                    )
                    logger.info(f"Sent additional message {i+1}/{len(additional_messages)}")
        else:
            logger.warning("No final response was generated to send.")

        return {"status": "success", "action_handled": action_type}

    except Exception as e:
        logger.error(f"Unhandled error in webhook_handler: {e}", exc_info=True)
        # Attempt to notify user of failure
        try:
            if conversation_id:
                ChatwootClient().send_message(
                    conversation_id=conversation_id,
                    message_text="I encountered an unexpected error. Please try again."
                )
        except Exception as notify_e:
            logger.error(f"Failed to send error notification to user: {notify_e}")
        return {"status": "error", "message": str(e)}


def _needs_calendar_data(message: str) -> bool:
    """
    Check if the message is asking for calendar information
    """
    message_lower = message.lower()
    calendar_query_keywords = [
        'meeting', 'meetings', 'schedule', 'calendar', 'event', 'events',
        'appointment', 'appointments', 'agenda', 'today', 'tomorrow',
        'this week', 'next week', 'what do i have', 'what\'s on',
        'show me my', 'list my'
    ]
    return any(keyword in message_lower for keyword in calendar_query_keywords)


def _needs_email_data(message: str) -> bool:
    """
    Check if the message is asking for email information
    """
    message_lower = message.lower()
    email_query_keywords = [
        'email', 'emails', 'mail', 'inbox', 'unread', 'messages',
        'summarize', 'summary', 'new emails', 'recent emails'
    ]
    return any(keyword in message_lower for keyword in email_query_keywords)


def _is_simple_question(message: str) -> bool:
    """
    Check if the message is a simple question that should be answered directly
    by the agent without needing action executors (calendar/email).
    """
    message_lower = message.lower()
    simple_question_patterns = [
        'what is today',
        "what's today",
        'what date',
        'what time',
        'current date',
        'current time',
        'today\'s date',
        "today's date",
        'what day is it',
        'what day is today',
    ]
    return any(pattern in message_lower for pattern in simple_question_patterns)


# ============================================================================
# Blueprint Route
# ============================================================================

@chatwoot_bp.route("/webhook", methods=["POST"])
def chatwoot_webhook():
    """
    Flask route for Chatwoot webhook
    """
    payload = request.get_json()
    result = webhook_handler(payload)
    return jsonify(result)
