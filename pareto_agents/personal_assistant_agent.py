import logging
from typing import Optional, Dict, Any
from agents import Agent, Runner
from .assistant_tools import (
    get_calendar_events,
    get_email_summary,
    get_daily_summary,
    ASSISTANT_TOOLS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Personal Assistant Agent Definition
# ============================================================================

personal_assistant_agent = Agent(
    name="Personal Assistant",
    tools=ASSISTANT_TOOLS,
    handoff_description="Specialist agent for complex multi-step tasks combining calendar and email operations",
    instructions=(
        "IMPORTANT: Today's date is 2025-12-29. You MUST use this date for all calculations. The user is in GMT+1. When the user asks for 'tomorrow', you must calculate the correct date (2025-12-30) and use it in your tool calls. You are a personal assistant that helps users with complex tasks involving calendar and email management. "
        "You have access to tools that allow you to:\n"
        "1. Get calendar events (today, specific date, week, or summary)\n"
        "2. Get email summaries (unread, recent, or search results)\n"
        "3. Generate combined daily summaries\n"
        "\n"
        "Your responsibilities:\n"
        "- Help users get summaries of their meetings and events\n"
        "- Provide lists of upcoming events or emails\n"
        "- Generate daily briefings combining calendar and email information\n"
        "- Answer questions about their schedule and communications\n"
        "\n"
        "When a user asks for information about their calendar or emails:\n"
        "1. Use the appropriate tool to fetch the data\n"
        "2. Format the results in a clear, readable way\n"
        "3. Provide helpful context and insights\n"
        "\n"
        "Be proactive and helpful. If a user asks for a summary, provide it in a well-organized format. "
        "Always be clear about what information you're retrieving and why."
    ),
)


# ============================================================================
# Task Routing Logic
# ============================================================================

def is_complex_task(message: str) -> bool:
    """
    Determine if a message requires the Personal Assistant (complex task)
    or can be handled directly by Calendar/Email agents (simple task)
    
    Complex tasks include:
    - Requests for summaries
    - Requests for lists/overviews
    - Multi-step operations
    - Comparative queries
    
    Simple tasks include:
    - Direct booking requests
    - Direct email sending
    - Single-step operations
    
    Args:
        message: User's message
        
    Returns:
        bool: True if complex task, False if simple task
    """
    message_lower = message.lower()
    
    # Complex task keywords
    complex_keywords = [
        'summary', 'summarize', 'overview', 'list', 'show me',
        'what are', 'how many', 'tell me about', 'brief',
        'schedule for', 'meetings on', 'events on', 'emails from',
        'unread', 'recent', 'upcoming', 'today', 'this week',
        'compare', 'between', 'combined', 'all my'
    ]
    
    # Simple task keywords
    simple_keywords = [
        'book', 'schedule', 'create', 'send', 'compose',
        'delete', 'cancel', 'update', 'reschedule',
        'mail me'
    ]
    
    # Check for complex keywords
    if any(keyword in message_lower for keyword in complex_keywords):
        return True
    
    # Check for simple keywords (if found, likely not complex)
    if any(keyword in message_lower for keyword in simple_keywords):
        return False
    
    # Default to complex for ambiguous cases
    return True


# ============================================================================
# Process Message with Personal Assistant
# ============================================================================

async def process_complex_task(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a complex task through the Personal Assistant agent
    
    Args:
        message: User's message
        phone_number: User's phone number
        user_data: User information from database
        
    Returns:
        dict: Processing result with response and metadata
    """
    try:
        logger.info(f"Processing complex task from {phone_number}: {message[:50]}...")
        
        runner = Runner()
        result = await runner.run(
            starting_agent=personal_assistant_agent,
            input=message,
            context={"phone_number": phone_number},
        )
        
        logger.info(f"Personal Assistant processing complete")
        
        # Extract response from result
        if hasattr(result, 'raw_responses') and result.raw_responses:
            last_response = result.raw_responses[-1] if isinstance(result.raw_responses, list) else result.raw_responses
            agent_response = last_response.output[0].content[0].text
        else:
            agent_response = str(result)
        
        logger.info(f"Personal Assistant response: {agent_response[:100]}...")
        
        return {
            "is_mail_me": False,
            "agent_response": agent_response,
            "action_type": "personal_assistant",
            "raw_result": result,
        }
    
    except Exception as e:
        logger.error(f"Error processing complex task: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error processing request: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }


# ============================================================================
# Synchronous Wrapper for Flask
# ============================================================================

def process_complex_task_sync(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for process_complex_task
    
    Args:
        message: User's message
        phone_number: User's phone number
        user_data: User information
        
    Returns:
        dict: Processing result
    """
    import asyncio
    
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async function
        result = loop.run_until_complete(
            process_complex_task(message, phone_number, user_data)
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error in sync wrapper: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }
