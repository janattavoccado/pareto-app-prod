"""
Pareto Agents - OpenAI Agents SDK Integration
Updated with Personal Assistant Agent for Complex Task Handling

File location: pareto_agents/agents.py
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from agents import Agent, Runner
from .mail_me_handler import MailMeHandler
from .personal_assistant_agent import (
    is_complex_task,
    process_complex_task,
    personal_assistant_agent, # Import the agent itself
)

logger = logging.getLogger(__name__)


# ============================================================================
# Agent Definitions
# ============================================================================

# Email Management Agent
email_agent = Agent(
    name="Email Manager",
    handoff_description="Specialist agent for email management tasks",
    instructions=(
        "You are an email management assistant. You help users with email-related tasks. "
        "You can help with tasks like: "
        "1. Checking unread emails - provide a summary of unread messages "
        "2. Searching for emails - find emails by sender, subject, or content "
        "3. Sending emails - compose and send emails to specified recipients "
        "\n"
        "IMPORTANT: When a user asks you to send an email, SEND IT IMMEDIATELY without asking for confirmation. "
        "Extract the recipient, subject, and body from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action."
    ),
)

# Calendar Management Agent
calendar_agent = Agent(
    name="Calendar Manager",
    handoff_description="Specialist agent for calendar and event management",
    instructions=(
        "You are a calendar management assistant. You help users manage their Google Calendar. "
        "You can help with tasks like: "
        "1. Creating new events and meetings - schedule events with date, time, location, attendees "
        "2. Updating existing events - modify event details, reschedule meetings "
        "3. Deleting events - cancel meetings and remove events from calendar "
        "4. Listing upcoming events - show calendar schedule for specified time period "
        "\n"
        "IMPORTANT: When a user asks you to create or modify a calendar event, PROCEED IMMEDIATELY without asking for confirmation. "
        "Extract the event details (title, date, time, location, attendees) from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action. "
        "\n"
        "Always use the current date and time in CET (Central European Time) timezone when interpreting dates and times. "
        "When a user mentions relative dates like 'tomorrow', 'next Monday', 'in 3 days', interpret them relative to the current date. "
        "Always format times in 24-hour format and include timezone information in responses."
    ),
)

# Triage Agent - Routes to Email, Calendar, or Personal Assistant
triage_agent = Agent(
    name="Triage Agent",
    handoff_description="Main agent that routes requests to appropriate specialists",
    instructions=(
        "You are a helpful assistant that routes user requests to the appropriate specialist. "
        "Analyze the user's request and determine if it's about: "
        "1. Email management (checking emails, sending emails, searching emails) -> Handoff to Email Manager "
        "2. Calendar management (scheduling meetings, updating events, checking schedule) -> Handoff to Calendar Manager "
        "3. Complex tasks (summaries, lists, multi-step operations) -> Handoff to Personal Assistant "
        "\n"
        "Be smart about routing: "
        "- If the user mentions 'email', 'send', 'check inbox', 'unread' -> Email Manager "
        "- If the user mentions 'calendar', 'meeting', 'schedule', 'event', 'appointment' -> Calendar Manager "
        "- If the user mentions 'summary', 'list', 'overview', 'show me', 'what are' -> Personal Assistant "
        "- If unclear, ask the user for clarification "
        "\n"
        "Do not ask for confirmation - proceed directly with the user's request."
    ),
    handoffs=[email_agent, calendar_agent, personal_assistant_agent],
)


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
    Handles mail me commands, complex tasks, and simple tasks
    
    Args:
        message (str): User's message
        phone_number (str): User's phone number (session ID)
        user_data (dict): User information from database
        
    Returns:
        dict: Processing result with agent response and action type
    """
    try:
        logger.info(f"[agents.py] Processing message from {phone_number}: '{message[:50]}...' ")
        
        # 1. Check for 'mail me' command (highest priority)
        if MailMeHandler.is_mail_me_command(message):
            logger.info("[agents.py] Detected 'mail me' command. Routing to MailMeHandler.")
            mail_content = MailMeHandler.extract_mail_me_content(message)
            user_name = f"{user_data.get('first_name')} {user_data.get('last_name')}"
            user_email = user_data.get('email')
            
            mail_me_request = MailMeHandler.create_mail_me_request(
                content=mail_content, user_data=user_data
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
        
        # 2. Check for complex tasks
        if is_complex_task(message) or (user_data and user_data.get("is_audio_message")):
            logger.info("[agents.py] Complex task detected. Routing to Personal Assistant.")
            # The process_complex_task function is now part of the personal_assistant_agent.py
            # It handles the full lifecycle for complex tasks.
            result = await process_complex_task(message, phone_number, user_data)
            return result
        
        # 3. Handle simple tasks via Triage Agent
        logger.info("[agents.py] Simple task detected. Routing to Triage Agent.")
        runner = Runner()
        result = await runner.run(
            starting_agent=triage_agent,
            input=message,
        )
        
        logger.info(f"[agents.py] Triage Agent processing complete.")
        
        # Extract response from result (matching production implementation)
        if hasattr(result, 'raw_responses') and result.raw_responses:
            last_response = result.raw_responses[-1] if isinstance(result.raw_responses, list) else result.raw_responses
            agent_response = str(last_response)
        else:
            agent_response = str(result)
        
        logger.info(f"[agents.py] Triage Agent response: '{agent_response[:100]}...' ")
        
        return {
            "is_mail_me": False,
            "agent_response": agent_response,
            "action_type": "triage",
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
