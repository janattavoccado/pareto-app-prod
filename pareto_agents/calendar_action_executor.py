"""
Calendar Action Executor with Pydantic + LLM Extraction and more
Parses agent responses using LLM + Pydantic instead of fragile regex
Handles natural language calendar operations with robust extraction

File location: pareto_agents/calendar_action_executor.py
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI

from .google_calendar_client import GoogleCalendarClient
from .user_manager_db_v2 import get_user_manager
from .timezone_service import TimezoneService
from .config_loader_v2 import get_google_user_token_by_phone

logger = logging.getLogger(__name__)


# ============================================================================
# Action Result Class (for Chatwoot compatibility)
# ============================================================================

class ActionResult:
    """Result object for action execution"""

    def __init__(self, action: str, success: bool, response: str, data: Optional[Dict] = None):
        """
        Initialize ActionResult

        Args:
            action (str): Action type (e.g., 'create_event')
            success (bool): Whether action succeeded
            response (str): Response message for user
            data (dict): Additional data from action
        """
        self.action = action
        self.success = success
        self.response = response
        self.data = data or {}


# ============================================================================
# Pydantic Models for Calendar Actions
# ============================================================================

class CreateEventRequest(BaseModel):
    """Structured calendar event creation request"""
    title: str = Field(..., description="Event title/topic")
    start_datetime: str = Field(..., description="Start time in natural language (e.g., 'tomorrow at 2pm')")
    end_datetime: Optional[str] = Field(None, description="End time in natural language")
    description: Optional[str] = Field(None, description="Event description/details")
    location: Optional[str] = Field(None, description="Event location")
    attendees: Optional[List[str]] = Field(None, description="List of attendee emails or names")

    class Config:
        str_strip_whitespace = True


class UpdateEventRequest(BaseModel):
    """Structured calendar event update request"""
    event_id: str
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class DeleteEventRequest(BaseModel):
    """Structured calendar event deletion request"""
    event_id: str


class ListEventsRequest(BaseModel):
    """Structured calendar events list request"""
    time_min: Optional[str] = None
    time_max: Optional[str] = None
    max_results: int = 10


# ============================================================================
# Calendar Action Executor
# ============================================================================

class CalendarActionExecutor:
    """
    Executes calendar actions based on agent responses
    Uses LLM + Pydantic for robust structured extraction
    """

    def __init__(self, user_phone: str):
        """
        Initialize executor for a specific user

        Args:
            user_phone (str): User phone number
        """
        self.user_phone = user_phone
        self.user_manager = get_user_manager()
        self.timezone_service = TimezoneService()
        self.calendar_client = None
        self.llm_client = OpenAI()  # Uses OPENAI_API_KEY env var
        self._initialize_calendar_client()

    def _initialize_calendar_client(self) -> None:
        """Initialize Google Calendar client for the user using database token"""
        try:
            # Get token data from database (not file path)
            token_data = get_google_user_token_by_phone(self.user_phone)
            if not token_data:
                logger.error(f"No Google token found in database for user {self.user_phone}")
                return

            # Pass token data directly to GoogleCalendarClient
            self.calendar_client = GoogleCalendarClient(token_data)
            logger.info(f"Calendar client initialized for {self.user_phone} using database token")

        except Exception as e:
            logger.error(f"Error initializing calendar client: {str(e)}", exc_info=True)

    def execute_action(self, response: Any) -> ActionResult:
        """
        Execute calendar action based on agent response

        Args:
            response: Agent response object

        Returns:
            ActionResult: Execution result with action, success, and response
        """
        try:
            # Extract text from response
            response_text = self._extract_response_text(response)
            logger.info(f"Extracted response text: {response_text[:100]}...")

            # Detect action type
            action_type = self._detect_action_type(response_text)
            logger.info(f"Detected action type: {action_type}")

            # Execute appropriate action
            if action_type == 'create_event':
                return self._execute_create_event(response_text)
            elif action_type == 'update_event':
                return self._execute_update_event(response_text)
            elif action_type == 'delete_event':
                return self._execute_delete_event(response_text)
            elif action_type == 'list_events':
                return self._execute_list_events(response_text)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return ActionResult(
                    action='unknown',
                    success=False,
                    response=f'Unknown action type: {action_type}'
                )

        except Exception as e:
            logger.error(f"Error executing calendar action: {str(e)}", exc_info=True)
            return ActionResult(
                action='error',
                success=False,
                response=f'Error executing calendar action: {str(e)}'
            )

    def _execute_create_event(self, response_text: str) -> ActionResult:
        """Execute create event action"""
        try:
            # Parse event details using LLM + Pydantic
            event_request = self._parse_create_event_llm(response_text)
            if not event_request:
                return ActionResult(
                    action='create_event',
                    success=False,
                    response='Could not parse event details from your message'
                )

            logger.info(f"Parsed event request: title={event_request.title}, start={event_request.start_datetime}")

            # Parse datetime
            start_dt = self.timezone_service.parse_datetime_string(event_request.start_datetime)
            if not start_dt:
                logger.error(f"Could not parse start datetime: {event_request.start_datetime}")
                return ActionResult(
                    action='create_event',
                    success=False,
                    response=f'Invalid start datetime: {event_request.start_datetime}'
                )

            # Parse end datetime if provided
            end_dt = None
            if event_request.end_datetime:
                end_dt = self.timezone_service.parse_datetime_string(event_request.end_datetime)

            # Create event
            result = self.calendar_client.create_event(
                title=event_request.title,
                start_datetime=start_dt,
                end_datetime=end_dt,
                description=event_request.description or "",
                location=event_request.location or "",
                attendees=event_request.attendees or []
            )

            if result.get('success'):
                # Format response message using parsed datetime (not LLM's string which may have wrong date)
                formatted_date = start_dt.strftime('%d %B %Y at %H:%M')
                response_msg = f"✅ Event '{event_request.title}' scheduled for {formatted_date}"
                logger.info(f"Event created successfully: {result}")
                return ActionResult(
                    action='create_event',
                    success=True,
                    response=response_msg,
                    data=result
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to create event: {error_msg}")
                return ActionResult(
                    action='create_event',
                    success=False,
                    response=f'Failed to create event: {error_msg}'
                )

        except Exception as e:
            logger.error(f"Error creating event: {str(e)}", exc_info=True)
            return ActionResult(
                action='create_event',
                success=False,
                response=f'Error creating event: {str(e)}'
            )

    def _execute_update_event(self, response_text: str) -> ActionResult:
        """Execute update event action"""
        try:
            event_request = self._parse_update_event(response_text)
            if not event_request:
                return ActionResult(
                    action='update_event',
                    success=False,
                    response='Could not parse update details'
                )

            result = self.calendar_client.update_event(
                event_id=event_request.event_id,
                title=event_request.title,
                start_datetime=None,
                end_datetime=None,
                description=event_request.description
            )

            if result.get('success'):
                return ActionResult(
                    action='update_event',
                    success=True,
                    response=f"✅ Event updated successfully",
                    data=result
                )
            else:
                return ActionResult(
                    action='update_event',
                    success=False,
                    response=f"Failed to update event: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return ActionResult(
                action='update_event',
                success=False,
                response=f'Error updating event: {str(e)}'
            )

    def _execute_delete_event(self, response_text: str) -> ActionResult:
        """Execute delete event action"""
        try:
            event_request = self._parse_delete_event(response_text)
            if not event_request:
                return ActionResult(
                    action='delete_event',
                    success=False,
                    response='Could not parse delete details'
                )

            result = self.calendar_client.delete_event(event_request.event_id)

            if result.get('success'):
                return ActionResult(
                    action='delete_event',
                    success=True,
                    response=f"✅ Event deleted successfully",
                    data=result
                )
            else:
                return ActionResult(
                    action='delete_event',
                    success=False,
                    response=f"Failed to delete event: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return ActionResult(
                action='delete_event',
                success=False,
                response=f'Error deleting event: {str(e)}'
            )

    def _execute_list_events(self, response_text: str) -> ActionResult:
        """Execute list events action - fetches and formats today's calendar events"""
        try:
            from datetime import datetime, timedelta
            
            # Determine time range from response text
            response_lower = response_text.lower()
            
            # Set time range based on keywords in the request
            now = datetime.utcnow()
            if 'tomorrow' in response_lower:
                time_min = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
                time_label = "tomorrow"
            elif 'this week' in response_lower or 'week' in response_lower:
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=7)
                time_label = "this week"
            else:  # Default to today
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
                time_label = "today"
            
            logger.info(f"Fetching calendar events for {time_label}: {time_min} to {time_max}")
            
            # Fetch events from Google Calendar
            result = self.calendar_client.get_events(
                time_min=time_min,
                time_max=time_max,
                max_results=20
            )

            if result.get('success'):
                events = result.get('events', [])
                logger.info(f"Retrieved {len(events)} events from calendar")
                
                if not events:
                    response_msg = f"📅 You have no events scheduled for {time_label}."
                else:
                    response_msg = f"📅 *Your {time_label}'s schedule ({len(events)} event(s)):*\n\n"
                    
                    for i, event in enumerate(events, 1):
                        title = event.get('summary', 'No title')
                        location = event.get('location', '')
                        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Unknown'))
                        end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date', ''))
                        
                        # Format the time nicely
                        try:
                            if 'T' in start:
                                dt_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                                time_str = dt_start.strftime('%H:%M')
                                if end and 'T' in end:
                                    dt_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                                    time_str += f" - {dt_end.strftime('%H:%M')}"
                            else:
                                time_str = 'All day'
                        except Exception as e:
                            logger.warning(f"Error formatting time: {e}")
                            time_str = start
                        
                        response_msg += f"{i}. *{title}*\n   🕐 {time_str}"
                        if location:
                            response_msg += f"\n   📍 {location}"
                        response_msg += "\n\n"
                
                return ActionResult(
                    action='list_events',
                    success=True,
                    response=response_msg.strip(),
                    data=result
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to list events: {error_msg}")
                return ActionResult(
                    action='list_events',
                    success=False,
                    response=f"❌ Failed to retrieve calendar events: {error_msg}"
                )

        except Exception as e:
            logger.error(f"Error listing events: {str(e)}", exc_info=True)
            return ActionResult(
                action='list_events',
                success=False,
                response=f'❌ Error listing events: {str(e)}'
            )

    def query_events(self, time_range: str = 'today') -> ActionResult:
        """
        Query calendar events for a specific time range.
        This method is for calendar QUERIES, not actions.

        Args:
            time_range: 'today', 'tomorrow', 'this_week', 'upcoming'

        Returns:
            ActionResult with formatted event list
        """
        try:
            from datetime import datetime, timedelta

            now = datetime.utcnow()

            if time_range == 'today':
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
            elif time_range == 'tomorrow':
                time_min = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
            elif time_range == 'this_week':
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=7)
            else:  # upcoming
                time_min = now
                time_max = None

            result = self.calendar_client.get_events(
                time_min=time_min,
                time_max=time_max,
                max_results=20
            )

            if result.get('success'):
                events = result.get('events', [])

                if not events:
                    response_msg = f"📅 You have no events scheduled for {time_range.replace('_', ' ')}."
                else:
                    response_msg = f"📅 **Your {time_range.replace('_', ' ')} schedule:**\n\n"
                    for event in events:
                        title = event.get('summary', 'No title')
                        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'Unknown'))

                        # Format the time nicely
                        try:
                            if 'T' in start:
                                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                                time_str = dt.strftime('%H:%M')
                            else:
                                time_str = 'All day'
                        except:
                            time_str = start

                        response_msg += f"• **{time_str}** - {title}\n"

                return ActionResult(
                    action='query_events',
                    success=True,
                    response=response_msg,
                    data=result
                )
            else:
                return ActionResult(
                    action='query_events',
                    success=False,
                    response=f"Failed to get events: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error querying events: {str(e)}", exc_info=True)
            return ActionResult(
                action='query_events',
                success=False,
                response=f'Error querying events: {str(e)}'
            )

    def _extract_response_text(self, response: Any) -> str:
        """Extract text from agent response"""
        try:
            # Handle RunResult from Anthropic
            if hasattr(response, 'output'):
                output = response.output
                if isinstance(output, list) and len(output) > 0:
                    first_output = output[0]
                    if hasattr(first_output, 'content'):
                        content = first_output.content
                        if isinstance(content, list) and len(content) > 0:
                            text_content = content[0]
                            if hasattr(text_content, 'text'):
                                return text_content.text

            return str(response)

        except Exception as e:
            logger.error(f"Error extracting text from response: {str(e)}")
            return str(response)

    def _detect_action_type(self, response_text: str) -> str:
        """
        Detect calendar action type from response

        Args:
            response_text (str): Response text

        Returns:
            str: Action type (create_event, update_event, delete_event, list_events)
        """
        response_lower = response_text.lower()

        # IMPORTANT: Check for list/query keywords FIRST to avoid false positives
        # Words like "schedule" can appear in both create and list contexts
        # Query/summary requests should be detected before create actions
        list_keywords = [
            'summarize', 'summary', 'what do i have', 'what\'s on', 'what is on',
            'show me', 'list', 'upcoming', 'today\'s', 'todays', 'tomorrow\'s',
            'this week', 'next week', 'my calendar', 'my events', 'my meetings',
            'check my', 'view my', 'get my', 'retrieve', 'fetch',
            'i\'ll need access', 'need access', 'provide a summary'
        ]
        if any(keyword in response_lower for keyword in list_keywords):
            return 'list_events'

        # Check for delete keywords (before create, as "cancel" is more specific)
        delete_keywords = ['delete', 'cancel', 'remove', 'cancelled']
        if any(keyword in response_lower for keyword in delete_keywords):
            return 'delete_event'

        # Check for update keywords
        update_keywords = ['update', 'change', 'reschedule', 'modify', 'moved to']
        if any(keyword in response_lower for keyword in update_keywords):
            return 'update_event'

        # Check for create/schedule keywords LAST
        # These are more generic and should only match if no other action fits
        create_keywords = [
            'meeting scheduled', 'event created', 'booked', 'scheduled for',
            'create', 'schedule', 'book', 'add', 'new event', 'set up'
        ]
        if any(keyword in response_lower for keyword in create_keywords):
            return 'create_event'

        return 'unknown'

    def _parse_create_event_llm(self, response_text: str) -> Optional[CreateEventRequest]:
        """
        Parse create event details using LLM + Pydantic

        Uses OpenAI API to extract structured data from agent response
        This is much more robust than regex!

        Args:
            response_text (str): Response text from agent

        Returns:
            CreateEventRequest: Parsed event request or None
        """
        try:
            logger.info(f"Parsing create event using LLM...")

            # Create extraction prompt - PRESERVE dates as-is, don't convert them
            extraction_prompt = f"""Extract calendar event details from the following agent response.
Return a JSON object with these fields:
- title: Event title/topic
- start_datetime: When meeting starts (PRESERVE exact format from agent response)
- end_datetime: When meeting ends (optional)
- description: Event details (optional)
- location: Event location (optional)
- attendees: List of email addresses (optional)

CRITICAL: PRESERVE the exact date format from the agent response.
Do NOT convert absolute dates to relative dates.

Examples of correct extraction:
- Agent says "19 December at 4pm" -> return "19 December at 4pm"
- Agent says "tomorrow at 2pm" -> return "tomorrow at 2pm"
- Agent says "Monday at 3pm" -> return "Monday at 3pm"

NEVER do this:
- Do NOT convert "19 December" to "in 6 days"
- Do NOT calculate or change the date
- Do NOT use relative dates if absolute dates are given

Agent response:
{response_text}

Return ONLY valid JSON, no other text."""

            # Call LLM to extract structured data
            response = self.llm_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a calendar event extraction assistant. Extract event details and return valid JSON. Preserve date formats exactly as given."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0,
                max_tokens=500
            )

            # Parse LLM response
            llm_response_text = response.choices[0].message.content.strip()
            logger.debug(f"LLM extraction response: {llm_response_text}")

            # Check if response is empty
            if not llm_response_text:
                logger.error("LLM returned empty response")
                return None

            # Try to extract JSON from response (in case there's extra text)
            json_start = llm_response_text.find('{')
            json_end = llm_response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.error(f"No JSON found in LLM response: {llm_response_text}")
                return None

            json_str = llm_response_text[json_start:json_end]
            logger.debug(f"Extracted JSON: {json_str}")

            # Parse JSON
            event_data = json.loads(json_str)

            # Filter attendees to only valid emails (skip invalid ones)
            raw_attendees = event_data.get('attendees', []) or []
            valid_attendees = []
            for attendee in raw_attendees:
                if isinstance(attendee, str) and '@' in attendee:
                    valid_attendees.append(attendee)

            # Validate with Pydantic
            event_request = CreateEventRequest(
                title=event_data.get('title', 'Meeting'),
                start_datetime=event_data.get('start_datetime', 'tomorrow at 2pm'),
                end_datetime=event_data.get('end_datetime'),
                description=event_data.get('description'),
                location=event_data.get('location'),
                attendees=valid_attendees if valid_attendees else None
            )

            logger.info(f"Successfully parsed event: title='{event_request.title}', start='{event_request.start_datetime}'")

            return event_request

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing create event with LLM: {str(e)}", exc_info=True)
            return None

    def _parse_update_event(self, response_text: str) -> Optional[UpdateEventRequest]:
        """Parse update event details"""
        try:
            # TODO: Implement LLM-based extraction for update
            return None
        except Exception as e:
            logger.error(f"Error parsing update event: {str(e)}")
            return None

    def _parse_delete_event(self, response_text: str) -> Optional[DeleteEventRequest]:
        """Parse delete event details"""
        try:
            # TODO: Implement LLM-based extraction for delete
            return None
        except Exception as e:
            logger.error(f"Error parsing delete event: {str(e)}")
            return None

    def _parse_list_events(self, response_text: str) -> ListEventsRequest:
        """Parse list events details"""
        try:
            # TODO: Implement LLM-based extraction for list
            return ListEventsRequest(max_results=10)
        except Exception as e:
            logger.error(f"Error parsing list events: {str(e)}")
            return ListEventsRequest(max_results=10)
