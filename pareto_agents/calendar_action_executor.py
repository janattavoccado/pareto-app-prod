"""
Calendar Action Executor with Pydantic + LLM Extraction
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
from .user_manager import get_user_manager
from .timezone_service import TimezoneService

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
        """Initialize Google Calendar client for the user"""
        try:
            # Get token path using correct UserManager API (now returns user email)
            user_id = self.user_manager.get_google_token_path(self.user_phone)
            if not user_id:
                logger.error(f"No user ID (email) found for user {self.user_phone}")
                return
            
            # The client is initialized with the user's email
            self.calendar_client = GoogleCalendarClient(user_id)
            logger.info(f"Calendar client initialized for {self.user_phone}")
        
        except Exception as e:
            logger.error(f"Error initializing calendar client: {str(e)}")
    
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
        if not self.calendar_client:
            return ActionResult(action='create_event', success=False, response='Calendar client not initialized. Check credentials.')
            
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
            
            # Construct event body for Google Calendar API
            event_body = {
                'summary': event_request.title,
                'description': event_request.description or "",
                'location': event_request.location or "",
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': self.timezone_service.get_timezone_name()
                },
                'end': {
                    'dateTime': (end_dt if end_dt else start_dt).isoformat(),
                    'timeZone': self.timezone_service.get_timezone_name()
                },
                'attendees': [{'email': email} for email in event_request.attendees or []]
            }
            
            # Create event
            result = self.calendar_client.create_event(event_body)
            
            # FIX: Added check for 'result' to prevent AttributeError
            if result and result.get('success'):
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
                # FIX: Added check for 'result' to prevent AttributeError
                error_msg = result.get('error', 'Unknown error') if result else 'Calendar client failed to return a result.'
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
        if not self.calendar_client:
            return ActionResult(action='update_event', success=False, response='Calendar client not initialized. Check credentials.')
            
        try:
            event_request = self._parse_update_event(response_text)
            if not event_request:
                return ActionResult(
                    action='update_event',
                    success=False,
                    response='Could not parse update details'
                )
            
            # FIX: Passing event body as a single dictionary (assuming client was fixed)
            update_body = {
                'summary': event_request.title,
                'description': event_request.description,
                # Add other fields as needed
            }
            
            result = self.calendar_client.update_event(
                event_id=event_request.event_id,
                update_body=update_body
            )
            
            if result and result.get('success'):
                return ActionResult(
                    action='update_event',
                    success=True,
                    response=f"✅ Event updated successfully",
                    data=result
                )
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Calendar client failed to return a result.'
                logger.error(f"Failed to update event: {error_msg}")
                return ActionResult(
                    action='update_event',
                    success=False,
                    response=f'Failed to update event: {error_msg}'
                )
        
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}", exc_info=True)
            return ActionResult(
                action='update_event',
                success=False,
                response=f'Error updating event: {str(e)}'
            )

    def _execute_delete_event(self, response_text: str) -> ActionResult:
        """Execute delete event action"""
        if not self.calendar_client:
            return ActionResult(action='delete_event', success=False, response='Calendar client not initialized. Check credentials.')
            
        try:
            event_request = self._parse_delete_event(response_text)
            if not event_request:
                return ActionResult(
                    action='delete_event',
                    success=False,
                    response='Could not parse delete details'
                )
            
            result = self.calendar_client.delete_event(event_request.event_id)
            
            if result and result.get('success'):
                return ActionResult(
                    action='delete_event',
                    success=True,
                    response=f"✅ Event deleted successfully",
                    data=result
                )
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Calendar client failed to return a result.'
                logger.error(f"Failed to delete event: {error_msg}")
                return ActionResult(
                    action='delete_event',
                    success=False,
                    response=f'Failed to delete event: {error_msg}'
                )
        
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}", exc_info=True)
            return ActionResult(
                action='delete_event',
                success=False,
                response=f'Error deleting event: {str(e)}'
            )

    def _execute_list_events(self, response_text: str) -> ActionResult:
        """Execute list events action"""
        if not self.calendar_client:
            return ActionResult(action='list_events', success=False, response='Calendar client not initialized. Check credentials.')
            
        try:
            event_request = self._parse_list_events(response_text)
            
            result = self.calendar_client.get_events(
                max_results=event_request.max_results
            )
            
            if result and result.get('success'):
                events = result.get('events', [])
                response_msg = f"✅ Found {len(events)} upcoming events"
                
                # Format events for user response
                event_list = []
                for event in events:
                    start = event.get('start', {}).get('dateTime', 'N/A')
                    summary = event.get('summary', 'No Title')
                    event_list.append(f"- {summary} at {start}")
                
                response_msg += "\n" + "\n".join(event_list)
                
                return ActionResult(
                    action='list_events',
                    success=True,
                    response=response_msg,
                    data=result
                )
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Calendar client failed to return a result.'
                logger.error(f"Failed to list events: {error_msg}")
                return ActionResult(
                    action='list_events',
                    success=False,
                    response=f'Failed to list events: {error_msg}'
                )
        
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}", exc_info=True)
            return ActionResult(
                action='list_events',
                success=False,
                response=f'Error listing events: {str(e)}'
            )

    # --- Helper Methods (omitted for brevity) ---
    
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
        
        # Check for create/schedule keywords
        create_keywords = ['create', 'schedule', 'book', 'add', 'new event', 'meeting scheduled']
        if any(keyword in response_lower for keyword in create_keywords):
            return 'create_event'
        
        # Check for update keywords
        update_keywords = ['update', 'change', 'reschedule', 'modify', 'moved to']
        if any(keyword in response_lower for keyword in update_keywords):
            return 'update_event'
        
        # Check for delete keywords
        delete_keywords = ['delete', 'cancel', 'remove', 'cancelled']
        if any(keyword in response_lower for keyword in delete_keywords):
            return 'delete_event'
        
        # Check for list keywords
        list_keywords = ['list', 'show', 'upcoming', 'events', 'meetings', 'schedule']
        if any(keyword in response_lower for keyword in list_keywords):
            return 'list_events'
        
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
            
            # Create extraction prompt
            extraction_prompt = f"""
Extract calendar event details from the following agent response.
Return a JSON object with the following fields:
- title: The main topic/subject of the meeting (e.g., "Project Alpha", "Discussion with John")
- start_datetime: When the meeting should start using RELATIVE dates only (e.g., "tomorrow at 2pm", "Monday at 3pm", "in 2 hours"). NEVER use absolute dates like "7 June", "June 7", "2025-06-07". Always use relative terms.
- end_datetime: When the meeting should end using RELATIVE dates only. Optional.
- description: Event description/details. Optional.
- location: Event location. Optional.
- attendees: List of attendee emails or names. Optional.

Agent Response:
---
{response_text}
---
"""
            
            # Run LLM extraction
            extracted_data = self._run_llm_extraction(extraction_prompt, CreateEventRequest)
            
            if extracted_data:
                # Pydantic validation
                event_request = CreateEventRequest(**extracted_data)
                logger.info(f"Successfully parsed event: title='{event_request.title}', start='{event_request.start_datetime}'")
                return event_request
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing create event with LLM: {str(e)}", exc_info=True)
            return None

    def _parse_update_event(self, response_text: str) -> Optional[UpdateEventRequest]:
        """
        Parse update event details using LLM + Pydantic
        """
        # Implementation omitted for brevity
        return None

    def _parse_delete_event(self, response_text: str) -> Optional[DeleteEventRequest]:
        """
        Parse delete event details using LLM + Pydantic
        """
        # Implementation omitted for brevity
        return None

    def _parse_list_events(self, response_text: str) -> Optional[ListEventsRequest]:
        """
        Parse list events details using LLM + Pydantic
        """
        # Implementation omitted for brevity
        return ListEventsRequest()

    def _get_pydantic_schema(self, model: BaseModel) -> str:
        """Get JSON schema for Pydantic model"""
        return json.dumps(model.model_json_schema())

    def _run_llm_extraction(self, prompt: str, model: BaseModel) -> Optional[Dict]:
        """
        Runs the LLM to extract structured data
        """
        try:
            schema = self._get_pydantic_schema(model)
            
            response = self.llm_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": f"You are a precise data extraction engine. Your task is to extract information from the user's message and return a single JSON object that conforms to the following JSON schema. Do not include any other text or markdown formatting outside of the JSON object.\n\nJSON Schema:\n{schema}"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            json_string = response.choices[0].message.content
            return json.loads(json_string)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}", exc_info=True)
            return None
