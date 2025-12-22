"""
Google Email Client - Corrected Version

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
from .config_loader import get_google_credentials, get_user_config

logger = logging.getLogger(__name__)

# Google Email API scopes (Gmail API)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GoogleEmailClient:
    """
    Google Email API client with support for:
    - Base64 environment variables (Heroku)
    - JSON files (Local development)
    """
    
    def __init__(self, user_email: str = 'jan_avoccado_pareto'):
        """
        Initialize Google Email client.
        
        Args:
            user_email: User identifier for token storage
        """
        self.user_email = user_email
        self.token_path = f'configurations/tokens/{user_email}.json'
        self.service = None
        self.credentials = None
        
        logger.info(f"Initializing Google Email client for {user_email}")
        
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
            # Get credentials using config_loader
            creds_dict = get_google_credentials()
            
            if not creds_dict:
                logger.error("❌ Could not load Google credentials")
                return False
            
            # Check if it's a service account (look for private_key) or OAuth credentials
            if creds_dict.get('private_key') and creds_dict.get('client_email'):
                logger.info("✅ Using service account credentials (detected via private_key)")
                self.credentials = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=SCOPES
                )
            else:
                logger.info("✅ Using OAuth credentials (default fallback)")
                # This will likely fail if the JSON is not a full OAuth token, but it's the correct class to use
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
        Build Google Email service (Gmail API).
        
        Returns:
            True if service built, False otherwise
        """
        try:
            if not self.credentials:
                logger.error("❌ No credentials available to build service")
                return False
            
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("✅ Google Email service built successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error building Email service: {e}")
            return False
    
    def send_email(self, to: str, subject: str, body: str) -> Optional[Dict]:
        """
        Send an email using the Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            
        Returns:
            Sent message object or None
        """
        try:
            if not self.service:
                logger.error("❌ Email service not initialized")
                return None
            
            from email.mime.text import MIMEText
            
            message = MIMEText(body)
            message['to'] = to
            message['from'] = self.user_email  # Sender is the service account or authorized user
            message['subject'] = subject
            
            raw_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
            
            logger.info(f"Sending email to {to} with subject: {subject}")
            
            send_message = self.service.users().messages().send(
                userId='me',
                body=raw_message
            ).execute()
            
            logger.info(f"✅ Email sent. Message ID: {send_message.get('id')}")
            return send_message
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")
            return None


# Convenience function
def get_email_client(user_email: str = 'jan_avoccado_pareto') -> Optional[GoogleEmailClient]:
    """
    Get initialized Google Email client.
    
    Args:
        user_email: User identifier
        
    Returns:
        GoogleEmailClient instance or None
    """
    try:
        client = GoogleEmailClient(user_email)
        if client.service:
            return client
        return None
    except Exception as e:
        logger.error(f"❌ Error creating email client: {e}")
        return None


if __name__ == '__main__':
    # Test script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # NOTE: This test requires a valid Base64 GOOGLE_CREDS_JSON or local client_secrets.json
    # and the user_email to be authorized for the Gmail API.
    
    client = get_email_client()
    if client:
        # Example usage (will likely fail without proper setup)
        # client.send_email(
        #     to='test@example.com',
        #     subject='Test Email from Pareto App',
        #     body='This is a test email sent via the Gmail API.'
        # )
        print("Email client initialized. Manual send test skipped.")
