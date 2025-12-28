"""
Personal Assistant Tools - Calendar and Email Operations
Implements tools for the Personal Assistant agent following OpenAI SDK documentation
https://github.com/openai/openai-agents-python/tree/main/examples/tools

File location: pareto_agents/assistant_tools.py
"""

import logging
from typing import Optional, List, Dict, Any
from agents import FunctionTool, function_tool, RunContextWrapper
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Input/Output Models (Pydantic)
# ============================================================================

class CalendarEventInput(BaseModel):
    """Input model for calendar operations"""
    
    operation: str = Field(..., description="Operation: 'list_today', 'list_date', 'list_week', 'get_summary'")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format (for list_date)")
    include_details: bool = Field(False, description="Include full event details")


class EmailSummaryInput(BaseModel):
    """Input model for email operations"""
    
    operation: str = Field(..., description="Operation: 'list_unread', 'get_summary', 'search'")
    search_query: Optional[str] = Field(None, description="Search query for email search")
    limit: int = Field(10, description="Maximum number of emails to return")


class TaskSummaryInput(BaseModel):
    """Input model for combined task summaries"""
    
    task_type: str = Field(..., description="Task type: 'daily_summary', 'weekly_summary', 'meeting_prep'")
    date: Optional[str] = Field(None, description="Date for summary (YYYY-MM-DD)")


# ============================================================================
# Calendar Tools
# ============================================================================

def get_calendar_events(
    ctx: RunContextWrapper[Any],
    operation: str,
    date: Optional[str] = None,
    include_details: bool = False,
) -> Dict[str, Any]:
    """
    Get calendar events for the user
    
    Operations:
    - 'list_today': Get today's events
    - 'list_date': Get events for a specific date
    - 'list_week': Get events for the current week
    - 'get_summary': Get a summary of upcoming events
    
    Args:
        phone_number: User's phone number
        operation: Operation to perform
        date: Date in YYYY-MM-DD format (for list_date)
        include_details: Include full event details
        
    Returns:
        Dictionary with events list and summary
    """
    try:
        from .google_calendar_client import GoogleCalendarClient
        from .config_loader_v2 import get_google_user_token_by_phone
        
        phone_number = ctx.context.get("phone_number")
        logger.info(f"Getting calendar events for {phone_number} | Operation: {operation}")
        
        # Get user token
        token = get_google_user_token_by_phone(phone_number)
        if not token:
            logger.error(f"No Google token found for {phone_number}")
            return {
                "success": False,
                "error": "No Google calendar access configured",
                "events": []
            }
        
        # Initialize calendar client
        calendar_client = GoogleCalendarClient(token)
        
        # Perform operation
        if operation == 'list_today':
            events = calendar_client.get_today_events()
            summary = f"You have {len(events)} event(s) today"
            
        elif operation == 'list_date' and date:
            logger.info(f"Received date from agent: {date}")
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # Fallback for other date formats if needed
                logger.warning(f"Could not parse date: {date}, attempting fallback")
                # Add more parsing logic here if necessary
                return {"success": False, "error": f"Invalid date format: {date}"}
            events_response = calendar_client.get_events(time_min=date_obj, time_max=date_obj + timedelta(days=1))
            events = events_response.get("events", [])
            summary = f"You have {len(events)} event(s) on {date}"
            
        elif operation == 'list_week':
            events = calendar_client.get_week_events()
            summary = f"You have {len(events)} event(s) this week"
            
        elif operation == 'get_summary':
            events = calendar_client.get_upcoming_events(days=7)
            summary = f"Upcoming events (next 7 days): {len(events)} event(s)"
            
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "events": []
            }
        
        # Format events
        formatted_events = []
        for event in events:
            event_info = {
                "title": event.get("summary", "Untitled"),
                "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
            }
            
            if include_details:
                event_info["description"] = event.get("description", "")
                event_info["location"] = event.get("location", "")
                event_info["attendees"] = len(event.get("attendees", []))
            
            formatted_events.append(event_info)
        
        logger.info(f"Retrieved {len(formatted_events)} calendar events")
        
        return {
            "success": True,
            "operation": operation,
            "summary": summary,
            "events": formatted_events,
            "count": len(formatted_events)
        }
        
    except Exception as e:
        logger.error(f"Error getting calendar events: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "events": []
        }


def format_calendar_list(events: List[Dict[str, Any]]) -> str:
    """
    Format calendar events as a simple text list
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Formatted text string
    """
    if not events:
        return "No events found."
    
    lines = []
    for i, event in enumerate(events, 1):
        start = event.get("start", "Unknown")
        title = event.get("title", "Untitled")
        lines.append(f"{i}. {title} - {start}")
    
    return "\n".join(lines)


# ============================================================================
# Email Tools
# ============================================================================

def get_email_summary(
    ctx: RunContextWrapper[Any],
    operation: str,
    search_query: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Get email summary for the user
    
    Operations:
    - 'list_unread': Get unread emails
    - 'get_summary': Get summary of recent emails
    - 'search': Search emails by query
    
    Args:
        phone_number: User's phone number
        operation: Operation to perform
        search_query: Search query for email search
        limit: Maximum number of emails to return
        
    Returns:
        Dictionary with emails list and summary
    """
    try:
        from .google_email_client import GoogleEmailClient
        from .config_loader_v2 import get_google_user_token_by_phone
        
        phone_number = ctx.context.get("phone_number")
        logger.info(f"Getting email summary for {phone_number} | Operation: {operation}")
        
        # Get user token
        token = get_google_user_token_by_phone(phone_number)
        if not token:
            logger.error(f"No Google token found for {phone_number}")
            return {
                "success": False,
                "error": "No Google email access configured",
                "emails": []
            }
        
        # Initialize email client
        email_client = GoogleEmailClient(token)
        
        # Perform operation
        if operation == 'list_unread':
            emails = email_client.get_unread_emails(limit=limit)
            summary = f"You have {len(emails)} unread email(s)"
            
        elif operation == 'get_summary':
            emails = email_client.get_recent_emails(limit=limit)
            summary = f"Recent emails: {len(emails)} message(s)"
            
        elif operation == 'search' and search_query:
            emails = email_client.search_emails(search_query, limit=limit)
            summary = f"Search results for '{search_query}': {len(emails)} message(s)"
            
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "emails": []
            }
        
        # Format emails
        formatted_emails = []
        for email in emails:
            email_info = {
                "from": email.get("from", "Unknown"),
                "subject": email.get("subject", "No Subject"),
                "date": email.get("date", "Unknown"),
            }
            formatted_emails.append(email_info)
        
        logger.info(f"Retrieved {len(formatted_emails)} emails")
        
        return {
            "success": True,
            "operation": operation,
            "summary": summary,
            "emails": formatted_emails,
            "count": len(formatted_emails)
        }
        
    except Exception as e:
        logger.error(f"Error getting email summary: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "emails": []
        }


def format_email_list(emails: List[Dict[str, Any]]) -> str:
    """
    Format emails as a simple text list
    
    Args:
        emails: List of email dictionaries
        
    Returns:
        Formatted text string
    """
    if not emails:
        return "No emails found."
    
    lines = []
    for i, email in enumerate(emails, 1):
        sender = email.get("from", "Unknown")
        subject = email.get("subject", "No Subject")
        lines.append(f"{i}. From: {sender}")
        lines.append(f"   Subject: {subject}")
    
    return "\n".join(lines)


# ============================================================================
# Combined Task Tools
# ============================================================================

def get_daily_summary(ctx: RunContextWrapper[Any]) -> Dict[str, Any]:
    """
    Get a combined daily summary (calendar + emails)
    
    Args:
        phone_number: User's phone number
        
    Returns:
        Dictionary with combined summary
    """
    try:
        phone_number = ctx.context.get("phone_number")
        logger.info(f"Generating daily summary for {phone_number}")
        
        # Get calendar events
        phone_number = ctx.context.get("phone_number")
        calendar_result = get_calendar_events(ctx, operation="list_today")
        
        # Get unread emails
        email_result = get_email_summary(ctx, operation="list_unread", limit=5)
        
        # Combine results
        summary_text = "📅 **Daily Summary**\n\n"
        
        if calendar_result.get("success"):
            summary_text += f"**Calendar:** {calendar_result.get('summary')}\n"
            if calendar_result.get("events"):
                summary_text += format_calendar_list(calendar_result.get("events"))
            summary_text += "\n\n"
        
        if email_result.get("success"):
            summary_text += f"**Emails:** {email_result.get('summary')}\n"
            if email_result.get("emails"):
                summary_text += format_email_list(email_result.get("emails"))
        
        return {
            "success": True,
            "summary": summary_text,
            "calendar": calendar_result,
            "emails": email_result
        }
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "summary": ""
        }


# ============================================================================
# Tool Registration for OpenAI SDK
# ============================================================================

# These functions will be registered as tools with the Personal Assistant agent
get_calendar_events = function_tool(get_calendar_events)
get_email_summary = function_tool(get_email_summary)
get_daily_summary = function_tool(get_daily_summary)

ASSISTANT_TOOLS = [
    get_calendar_events,
    get_email_summary,
    get_daily_summary,
]
