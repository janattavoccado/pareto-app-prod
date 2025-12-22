"""
Google Email Client - Updated Version

Uses config_loader to read credentials from:
- Base64 environment variables (Heroku)
- JSON files (Local Windows development)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import the config loader
from config_loader import get_google_credentials, get_user_config

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GoogleEmailClient:
    """
    Google Gmail API client with support for:
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
            
            # Check if it's a service account or OAuth credentials
            if creds_dict.get('type') == 'service_account':
                logger.info("✅ Using service account credentials")
                self.credentials = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=SCOPES
                )
            else:
                logger.info("✅ Using OAuth credentials")
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
        Build Google Gmail service.
        
        Returns:
            True if service built, False otherwise
        """
        try:
            if not self.credentials:
                logger.error("❌ No credentials available to build service")
                return False
            
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("✅ Google Gmail service built successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error building Gmail service: {e}")
            return False
    
    def get_sender_email(self) -> Optional[str]:
        """
        Get sender email address from user config.
        
        Returns:
            Email address or None
        """
        try:
            user_config = get_user_config()
            
            if not user_config:
                logger.error("❌ Could not load user configuration")
                return None
            
            # Get email for this user
            if self.user_email in user_config:
                email = user_config[self.user_email].get('email')
                if email:
                    logger.info(f"✅ Sender email found: {email}")
                    return email
            
            logger.error(f"❌ Email not found for user {self.user_email}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting sender email: {e}")
            return None
    
    def _create_message(self, to: str, subject: str, message_text: str, 
                       html: bool = False) -> Optional[Dict]:
        """
        Create a message for sending via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body (plain text or HTML)
            html: Whether message_text is HTML
            
        Returns:
            Message dictionary or None
        """
        try:
            sender = self.get_sender_email()
            if not sender:
                logger.error("❌ Could not get sender email")
                return None
            
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            
            if html:
                message.attach(MIMEText(message_text, 'html'))
            else:
                message.attach(MIMEText(message_text, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            return {'raw': raw_message}
            
        except Exception as e:
            logger.error(f"❌ Error creating message: {e}")
            return None
    
    def send_email(self, to: str, subject: str, message_text: str, 
                  html: bool = False) -> Optional[Dict]:
        """
        Send an email via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body (plain text or HTML)
            html: Whether message_text is HTML
            
        Returns:
            Sent message or None
        """
        try:
            if not self.service:
                logger.error("❌ Gmail service not initialized")
                return None
            
            logger.info(f"Sending email to {to}: {subject}")
            
            # Create message
            message = self._create_message(to, subject, message_text, html)
            if not message:
                logger.error("❌ Could not create message")
                return None
            
            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"✅ Email sent successfully (ID: {sent_message['id']})")
            return sent_message
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")
            return None
    
    def send_email_with_attachments(self, to: str, subject: str, 
                                   message_text: str, attachments: List[str] = None,
                                   html: bool = False) -> Optional[Dict]:
        """
        Send an email with attachments via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body (plain text or HTML)
            attachments: List of file paths to attach
            html: Whether message_text is HTML
            
        Returns:
            Sent message or None
        """
        try:
            if not self.service:
                logger.error("❌ Gmail service not initialized")
                return None
            
            sender = self.get_sender_email()
            if not sender:
                logger.error("❌ Could not get sender email")
                return None
            
            logger.info(f"Sending email with attachments to {to}: {subject}")
            
            # Create multipart message
            message = MIMEMultipart()
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            
            # Add body
            if html:
                message.attach(MIMEText(message_text, 'html'))
            else:
                message.attach(MIMEText(message_text, 'plain'))
            
            # Add attachments
            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                
                for attachment_path in attachments:
                    try:
                        path = Path(attachment_path)
                        if path.exists():
                            with open(path, 'rb') as attachment:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(attachment.read())
                                encoders.encode_base64(part)
                                part.add_header(
                                    'Content-Disposition',
                                    f'attachment; filename= {path.name}'
                                )
                                message.attach(part)
                                logger.info(f"✅ Attached: {path.name}")
                    except Exception as e:
                        logger.error(f"❌ Error attaching {attachment_path}: {e}")
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"✅ Email with attachments sent (ID: {sent_message['id']})")
            return sent_message
            
        except HttpError as e:
            logger.error(f"❌ Google API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error sending email with attachments: {e}")
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
    
    client = get_email_client()
    if client:
        # Test sending email
        result = client.send_email(
            to='test@example.com',
            subject='Test Email',
            message_text='This is a test email from Pareto Agent.'
        )
        if result:
            print(f"Email sent successfully: {result['id']}")
