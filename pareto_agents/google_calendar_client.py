"""
Google Calendar Client - Corrected Version

Uses config_loader to read credentials from:
- Base64 environment variables (Heroku)
- JSON files (Local Windows development)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import google.auth.exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import the config loader using RELATIVE IMPORT
from .config_loader import get_google_client_secrets, get_google_user_token, get_user_config

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """
    Google Calendar API client with support for:
    - Base64 environment variables (Heroku)
    - JSON files (Local development)
    """
    
    def __init__(self, user_email: str = 'jan_avoccado_pareto'):
        """
        Initialize Google Calendar client.
        
        Args:
            user_email: User identifier for token storage
        """
        self.user_email = user_email
        self.token_path = f'configurations/tokens/{user_email}.json'
        self.service = None
        self.credentials = None
        
        logger.info(f"Initializing Google Calendar client for {user_email}")
        
        # Load credentials
        self._load_credentials()
        
        if self.credentials:
            self._build_service()
    
    def _load_credentials(self) -> bool:
        """
        Load Google credentials from config loader.
        
        Returns:
            True if credentials loaded, False otherwise
        """
        try:
            # 1. Get the user's token (jan_avoccado_pareto.json content)
            token_dict = get_google_user_token()
            client_secrets = get_google_client_secrets()
            
            if not token_dict or not client_secrets:
                logger.error("❌ Could not load Google user token or client secrets")
                return False
            
            # 2. Load as UserCredentials (which is what the token.json contains)
            # The token file is the result of the OAuth flow, so it's a UserCredentials object.
            logger.info("✅ Using OAuth User Token credentials")
            
            # Merge client secrets into token dict for refresh to work
            creds_dict = {**token_dict, **client_secrets.get('installed', {})}
            
            self.credentials = UserCredentials.from_authorized_user_info(
                creds_dict,
                scopes=SCOPES
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading credentials: {e}")
            return False
    
    def _build_service(self) -> bool:
        """
        Build Google Calendar service.
        
        Returns:
            True if service built, False otherwise
        """
        try:
            if not self.credentials:
                logger.error("❌ No credentials available to build service")
                return False
            
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("✅ Google Calendar service built successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error building Calendar service: {e}")
            return False
    
    def get_calendar_id(self) -> Optional[str]:
        """
        Get calendar ID from user config.
        
        Returns:
            Calendar ID or None
        """
        try:
            user_config = get_user_config()
            
            if not user_config:
                logger.error("❌ Could not load user configuration")
                return None
            
            # Get calendar ID for this user
            if self.user_email in user_config:
                calendar_id = user_config[self.user_email].get('calendar_id')
                if calendar_id:
                    logger.info(f"✅ Calendar ID found: {calendar_id}")
                    return calendar_id
            
            logger.error(f"❌ Calendar ID not found for user {self.user_email}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting calendar ID: {e}")
            return None
    
    def create_event(self, event_data: Dict) -> Optional[Dict]:
        """
        Create a calendar event.
        
        Args:
            event_data: Event details (summary, start, end, description, etc.)
            
        Returns:
            Created event or None
        """
        try:
            if not self.service:
                logger.error("❌ Calendar service not initialized")
                return None
            
            calendar_id = self.get_calendar_id()
            if not calendar_id:
                logger.error("❌ Could not get calendar ID")
                return None
            
            logger.info(f"Creating event: {event_data.get('summary')}")
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            logger.info(f"✅ Event created: {event.get('id')}")
            return event
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error creating event: {e}")
            return None
    
    def update_event(self, event_id: str, event_data: Dict) -> Optional[Dict]:
        """
        Update a calendar event.
        
        Args:
            event_id: ID of event to update
            event_data: Updated event details
            
        Returns:
            Updated event or None
        """
        try:
            if not self.service:
                logger.error("❌ Calendar service not initialized")
                return None
            
            calendar_id = self.get_calendar_id()
            if not calendar_id:
                logger.error("❌ Could not get calendar ID")
                return None
            
            logger.info(f"Updating event: {event_id}")
            
            event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            
            logger.info(f"✅ Event updated: {event_id}")
            return event
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error updating event: {e}")
            return None
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: ID of event to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            if not self.service:
                logger.error("❌ Calendar service not initialized")
                return False
            
            calendar_id = self.get_calendar_id()
            if not calendar_id:
                logger.error("❌ Could not get calendar ID")
                return False
            
            logger.info(f"Deleting event: {event_id}")
            
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"✅ Event deleted: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting event: {e}")
            return False
    
    def list_events(self, max_results: int = 10) -> Optional[List[Dict]]:
        """
        List upcoming calendar events.
        
        Args:
            max_results: Maximum number of events to return
            
        Returns:
            List of events or None
        """
        try:
            if not self.service:
                logger.error("❌ Calendar service not initialized")
                return None
            
            calendar_id = self.get_calendar_id()
            if not calendar_id:
                logger.error("❌ Could not get calendar ID")
                return None
            
            logger.info(f"Listing {max_results} upcoming events")
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"✅ Found {len(events)} events")
            return events
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error listing events: {e}")
            return None


# Convenience function
def get_calendar_client(user_email: str = 'jan_avoccado_pareto') -> Optional[GoogleCalendarClient]:
    """
    Get initialized Google Calendar client.
    
    Args:
        user_email: User identifier
        
    Returns:
        GoogleCalendarClient instance or None
    """
    try:
        client = GoogleCalendarClient(user_email)
        if client.service:
            return client
        return None
    except Exception as e:
        logger.error(f"❌ Error creating calendar client: {e}")
        return None


if __name__ == '__main__':
    # Test script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    client = get_calendar_client()
    if client:
        events = client.list_events(5)
        if events:
            for event in events:
                print(f"- {event['summary']} ({event['start']})")
