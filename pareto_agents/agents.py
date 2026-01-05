"""
Pareto Agents - OpenAI Agents SDK Integration for Pareto
Updated with improved routing logic for Email, Calendar, and Personal Assistant agents

File location: pareto_agents/agents.py
"""

import logging
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any
import pytz

from agents import Agent, Runner
from .mail_me_handler import MailMeHandler

logger = logging.getLogger(__name__)

# Default timezone for the application
DEFAULT_TIMEZONE = pytz.timezone('Europe/Stockholm')  # CET/CEST


def get_current_datetime_context() -> str:
    """
    Get the current date and time formatted for agent context.
    Returns a string with current date, time, and day of week.
    """
    now = datetime.now(DEFAULT_TIMEZONE)
    return (
        f"Current date and time: {now.strftime('%A, %d %B %Y at %H:%M')} "
        f"(Timezone: {DEFAULT_TIMEZONE.zone}). "
        f"Today is {now.strftime('%A')}. "
        f"Tomorrow is {(now + __import__('datetime').timedelta(days=1)).strftime('%A, %d %B %Y')}."
    )


# ============================================================================
# Agent Definitions
# ============================================================================

# Email Management Agent - For direct email actions (send, compose)
email_agent = Agent(
    name="Email Manager",
    handoff_description="Specialist agent for email management tasks like sending emails",
    instructions=(
        "You are an email management assistant. You help users with email-related tasks. "
        "You can help with tasks like: "
        "1. Sending emails - compose and send emails to specified recipients "
        "2. Composing drafts - create email drafts for review "
        "\n"
        "IMPORTANT: When a user asks you to send an email, SEND IT IMMEDIATELY without asking for confirmation. "
        "Extract the recipient, subject, and body from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action."
    ),
)

# Calendar Management Agent - For direct calendar actions (book, create, update, delete)
calendar_agent = Agent(
    name="Calendar Manager",
    handoff_description="Specialist agent for calendar actions like booking meetings",
    instructions=(
        "You are a calendar management assistant. You help users manage their Google Calendar. "
        "You can help with tasks like: "
        "1. Creating new events and meetings - schedule events with date, time, location, attendees "
        "2. Updating existing events - modify event details, reschedule meetings "
        "3. Deleting events - cancel meetings and remove events from calendar "
        "\n"
        "CRITICAL: The message will contain a [SYSTEM: ...] section with the CURRENT DATE AND TIME. "
        "You MUST use this date/time information to correctly interpret relative dates like 'tomorrow', 'next Monday', 'today'. "
        "NEVER guess or hallucinate dates - always calculate from the provided current date. "
        "\n"
        "IMPORTANT: When a user asks you to create or modify a calendar event, PROCEED IMMEDIATELY without asking for confirmation. "
        "Extract the event details (title, date, time, location, attendees) from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed with the EXACT date you scheduled it for. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action. "
        "\n"
        "Always format times in 24-hour format and include the full date (day, month, year) in responses."
    ),
)

# Personal Assistant Agent - For queries, summaries, and general conversation
personal_assistant_agent = Agent(
    name="Personal Assistant",
    handoff_description="Specialist agent for queries, summaries, and general assistance",
    instructions=(
        "You are a helpful personal assistant. You help users with: "
        "1. Calendar queries - 'What meetings do I have today?', 'Show my schedule for tomorrow' "
        "2. Email queries - 'Summarize my unread emails', 'What new emails do I have?' "
        "3. Daily summaries - 'Give me a summary of my day', 'What's on my agenda?' "
        "4. General conversation - Greetings, questions, and general assistance "
        "5. Date and time questions - 'What is today's date?', 'What time is it?' "
        "\n"
        "CRITICAL: The message will contain a [SYSTEM: ...] section with the CURRENT DATE AND TIME. "
        "When a user asks about the current date, time, or day of week, use this information to provide an accurate answer. "
        "\n"
        "When a user asks about their calendar or emails, retrieve the relevant information and present it clearly. "
        "For greetings like 'Hello', respond warmly and ask how you can help. "
        "Be friendly, helpful, and proactive in offering assistance."
    ),
)


# ============================================================================
# Message Classification
# ============================================================================

def classify_message(message: str) -> str:
    """
    Classify the message to determine which agent should handle it.

    Returns:
        str: One of 'mail_me', 'calendar_action', 'email_action', 'personal_assistant'
    """
    message_lower = message.lower().strip()

    # 1. Check for 'mail me' command (highest priority)
    if MailMeHandler.is_mail_me_command(message):
        return 'mail_me'

    # 2. Check for direct calendar ACTIONS (booking, creating, updating, deleting)
    # Includes both English and Swedish keywords for multilingual support
    calendar_action_patterns = [
        # English patterns
        r'\b(book|schedule|create|set up|arrange)\b.*(meeting|appointment|event|call)',
        r'\b(update|change|modify|reschedule|move)\b.*(meeting|appointment|event)',
        r'\b(delete|cancel|remove)\b.*(meeting|appointment|event)',
        r'\badd\b.*(to|on).*(calendar|schedule)',
        r'\bbook me\b',
        r'\bschedule me\b',
        # Swedish patterns (boka=book, möte=meeting, kalender=calendar, avboka=cancel)
        r'\b(boka|skapa|lägg till|arrangera|planera)\b.*(möte|möten|händelse|samtal|event)',
        r'\b(ändra|flytta|uppdatera|byt)\b.*(möte|möten|händelse)',
        r'\b(avboka|ta bort|radera|ställ in)\b.*(möte|möten|händelse)',
        r'\blägg\b.*(i|på).*(kalender|kalendern|schema)',
        r'\bboka\s+(ett\s+)?möte\b',
        r'\bett\s+möte\b.*\b(imorgon|idag|nästa)\b',
    ]

    for pattern in calendar_action_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched calendar action pattern: {pattern}")
            return 'calendar_action'

    # 3. Check for direct email ACTIONS (sending, composing)
    # Includes both English and Swedish keywords for multilingual support
    email_action_patterns = [
        # English patterns
        r'\b(send|compose|write|draft)\b.*(email|mail|message)',
        r'\bemail\b.*(to|about)',
        r'\bsend\b.*(to)\b',
        # Swedish patterns (skicka=send, mejl/mail/e-post=email, meddelande=message)
        r'\b(skicka|skriv|författa)\b.*(mejl|mail|e-post|epost|meddelande)',
        r'\bmejla\b.*(till|om)',
        r'\bskicka\b.*(till)\b',
    ]

    for pattern in email_action_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched email action pattern: {pattern}")
            return 'email_action'

    # 4. Everything else goes to Personal Assistant (queries, summaries, greetings)
    # This includes:
    # - "What meetings do I have today?"
    # - "Summarize my emails"
    # - "Hello"
    # - "Show my schedule"
    # - "What's on my agenda?"
    # - General questions

    return 'personal_assistant'


# ============================================================================
# Process Message Function
# ============================================================================

async def process_message(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process incoming message through agents
    Routes to appropriate agent based on message classification

    Args:
        message (str): User's message
        phone_number (str): User's phone number (session ID)
        user_data (dict): User information from database

    Returns:
        dict: Processing result with agent response and action type
    """
    try:
        logger.info(f"[agents.py] Processing message from {phone_number}: '{message[:50]}...'")

        # Get current date/time context
        datetime_context = get_current_datetime_context()
        logger.info(f"[agents.py] DateTime context: {datetime_context}")

        # Classify the message
        message_type = classify_message(message)
        logger.info(f"[agents.py] Message classified as: {message_type}")
        
        # Prepend datetime context to message for agent processing
        message_with_context = f"[SYSTEM: {datetime_context}]\n\nUser message: {message}"

        # 1. Handle 'mail me' command
        if message_type == 'mail_me':
            logger.info("[agents.py] Routing to MailMeHandler.")
            mail_content = MailMeHandler.extract_mail_me_content(message)
            user_name = f"{user_data.get('first_name')} {user_data.get('last_name')}"
            user_email = user_data.get('email')

            mail_me_request = MailMeHandler.create_mail_me_request(
                content=mail_content, user_email=user_email, user_name=user_name
            )

            response = MailMeHandler.format_mail_me_response(
                user_name=user_name, subject=mail_me_request.subject, recipient=user_email
            )

            return {
                "is_mail_me": True,
                "agent_response": response,
                "action_type": "mail_me",
                "mail_me_request": mail_me_request,
            }

        # 2. Handle calendar actions (book, create, update, delete)
        if message_type == 'calendar_action':
            logger.info("[agents.py] Routing to Calendar Manager for action.")
            runner = Runner()
            result = await runner.run(
                starting_agent=calendar_agent,
                input=message_with_context,
            )

            agent_response = _extract_response(result)
            logger.info(f"[agents.py] Calendar Manager response: '{agent_response[:100]}...'")

            return {
                "is_mail_me": False,
                "agent_response": agent_response,
                "action_type": "calendar",
                "raw_result": result,
            }

        # 3. Handle email actions (send, compose)
        if message_type == 'email_action':
            logger.info("[agents.py] Routing to Email Manager for action.")
            runner = Runner()
            result = await runner.run(
                starting_agent=email_agent,
                input=message_with_context,
            )

            agent_response = _extract_response(result)
            logger.info(f"[agents.py] Email Manager response: '{agent_response[:100]}...'")

            return {
                "is_mail_me": False,
                "agent_response": agent_response,
                "action_type": "email",
                "raw_result": result,
            }

        # 4. Handle queries, summaries, and general conversation via Personal Assistant
        logger.info("[agents.py] Routing to Personal Assistant.")
        runner = Runner()
        result = await runner.run(
            starting_agent=personal_assistant_agent,
            input=message_with_context,
        )

        agent_response = _extract_response(result)
        logger.info(f"[agents.py] Personal Assistant response: '{agent_response[:100]}...'")

        return {
            "is_mail_me": False,
            "agent_response": agent_response,
            "action_type": "personal_assistant",
            "raw_result": result,
        }

    except Exception as e:
        logger.error(f"[agents.py] Error processing message: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error processing message: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }


def _extract_response(result) -> str:
    """
    Extract the text response from an agent result
    """
    if hasattr(result, 'final_output') and result.final_output:
        return str(result.final_output)
    if hasattr(result, 'raw_responses') and result.raw_responses:
        last_response = result.raw_responses[-1] if isinstance(result.raw_responses, list) else result.raw_responses
        return str(last_response)
    return str(result)


# ============================================================================
# Synchronous Wrapper for Flask
# ============================================================================

def process_message_sync(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for process_message for Flask compatibility.
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async function
        result = loop.run_until_complete(
            process_message(message, phone_number, user_data)
        )

        return result

    except Exception as e:
        logger.error(f"[agents.py] Error in sync wrapper: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }
