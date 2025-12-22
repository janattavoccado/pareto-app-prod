"""
Google Calendar Client for managing calendar events
Uses timezone_service for timezone handling (NO ZoneInfo)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pareto_agents.timezone_service import TimezoneService

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    Google Calendar API client for creating and managing events
    Uses TimezoneService for timezone handling
    """
    
    TIMEZONE_CET = "Europe/Zagreb"
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    
    def __init__(self, token_path: str):
        """
        Initialize Google Calendar client
        
        Args:
            token_path (str): Path to OAuth2 token file
        """
        self.token_path = token_path
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize Google Calendar service with OAuth2 token"""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            import json
            
            # Load credentials from token file
            with open(self.token_path, 'r') as f:
                token_data = json.load(f)
            
            creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            
            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info(f"Token refreshed for {self.token_path}")
            
            # Build service
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info(f"Google Calendar service initialized with token: {self.token_path}")
        
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {str(e)}", exc_info=True)
            raise
    
    def create_event(
        self,
        title: str,
        start_datetime: datetime,
        end_datetime: Optional[datetime] = None,
        description: str = "",
        attendees: Optional[List[str]] = None,
        location: str = ""
    ) -> Dict[str, Any]:
        """
        Create a calendar event
        
        Args:
            title (str): Event title
            start_datetime (datetime): Event start time (naive datetime in CET)
            end_datetime (datetime): Event end time (naive datetime in CET)
            description (str): Event description
            attendees (List[str]): List of attendee emails
            location (str): Event location
            
        Returns:
            dict: Event creation result with success status and event details
        """
        try:
            # Ensure we have a service
            if self.service is None:
                self._initialize_service()
            
            # If no end time, set to 1 hour after start
            if end_datetime is None:
                end_datetime = start_datetime + timedelta(hours=1)
            
            # Convert naive datetimes to ISO format strings
            # Google Calendar API expects ISO 8601 format with timezone
            start_str = start_datetime.isoformat()
            end_str = end_datetime.isoformat()
            
            logger.debug(f"Creating event: {title}")
            logger.debug(f"  Start: {start_str}")
            logger.debug(f"  End: {end_str}")
            logger.debug(f"  Timezone: {self.TIMEZONE_CET}")
            
            # Build event object
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_str,
                    'timeZone': self.TIMEZONE_CET,
                },
                'end': {
                    'dateTime': end_str,
                    'timeZone': self.TIMEZONE_CET,
                },
            }
            
            # Add location if provided
            if location:
                event['location'] = location
            
            # Add attendees if provided
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Create event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendNotifications=True
            ).execute()
            
            logger.info(f"Event created successfully: {created_event['id']}")
            logger.info(f"  Title: {created_event['summary']}")
            logger.info(f"  Start: {created_event['start'].get('dateTime', created_event['start'].get('date'))}")
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'event': created_event,
                'title': created_event['summary'],
                'start': created_event['start'].get('dateTime', created_event['start'].get('date')),
            }
        
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error creating event: {str(e)}",
            }
    
    def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Get calendar events
        
        Args:
            time_min (datetime): Minimum time (inclusive)
            time_max (datetime): Maximum time (exclusive)
            max_results (int): Maximum number of results
            
        Returns:
            dict: List of events
        """
        try:
            if self.service is None:
                self._initialize_service()
            
            kwargs = {
                'calendarId': 'primary',
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
            }
            
            if time_min:
                kwargs['timeMin'] = time_min.isoformat() + 'Z'
            
            if time_max:
                kwargs['timeMax'] = time_max.isoformat() + 'Z'
            
            events = self.service.events().list(**kwargs).execute()
            
            return {
                'success': True,
                'events': events.get('items', []),
            }
        
        except Exception as e:
            logger.error(f"Error getting events: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error getting events: {str(e)}",
            }
    
    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event
        
        Args:
            event_id (str): Event ID
            
        Returns:
            dict: Deletion result
        """
        try:
            if self.service is None:
                self._initialize_service()
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            logger.info(f"Event deleted: {event_id}")
            
            return {
                'success': True,
                'event_id': event_id,
            }
        
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error deleting event: {str(e)}",
            }
    
    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a calendar event
        
        Args:
            event_id (str): Event ID
            title (str): New event title
            start_datetime (datetime): New start time
            end_datetime (datetime): New end time
            description (str): New description
            
        Returns:
            dict: Update result
        """
        try:
            if self.service is None:
                self._initialize_service()
            
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Update fields
            if title:
                event['summary'] = title
            
            if description:
                event['description'] = description
            
            if start_datetime:
                event['start'] = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': self.TIMEZONE_CET,
                }
            
            if end_datetime:
                event['end'] = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': self.TIMEZONE_CET,
                }
            
            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Event updated: {event_id}")
            
            return {
                'success': True,
                'event_id': updated_event['id'],
                'event': updated_event,
            }
        
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Error updating event: {str(e)}",
            }
