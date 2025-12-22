"""
Google Gmail API Client - FIXED
Handles email operations using Google API with user-specific credentials
Includes proper error handling and API response verification
Supports Base64 environment variables for Heroku and local files for development

File location: pareto_agents/google_email_client.py
"""

import logging
import os
import json
import base64
from typing import Optional, List, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import googleapiclient.discovery
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleEmailClient:
    """
    Client for interacting with Google Gmail API
    Handles email operations with user-specific OAuth credentials
    Supports both Base64 env vars (Heroku) and file paths (Local)
    """
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, token_path: str, client_secrets_path: str = "configurations/client_secrets.json"):
        """
        Initialize Google Email Client with user's token
        
        Args:
            token_path (str): Path to user's Google OAuth token file (or env var name for Heroku)
            client_secrets_path (str): Path to client_secrets.json from Google Console
        """
        self.token_path = token_path
        self.client_secrets_path = client_secrets_path
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _load_token_data(self) -> Dict[str, Any]:
        """
        Load token data from either Base64 env var or file
        
        Returns:
            dict: Token data
        """
        # Try to load from Base64 environment variable first (Heroku)
        if self.token_path == 'GOOGLE_USER_TOKEN_JSON':
            env_value = os.getenv('GOOGLE_USER_TOKEN_JSON')
            if env_value:
                try:
                    decoded = base64.b64decode(env_value).decode('utf-8')
                    token_data = json.loads(decoded)
                    logger.info("✅ Loaded Google User Token from Base64 environment variable")
                    return token_data
                except Exception as e:
                    logger.error(f"❌ Error decoding GOOGLE_USER_TOKEN_JSON: {e}")
        
        # Fall back to file path (Local development)
        try:
            if not os.path.exists(self.token_path):
                raise FileNotFoundError(f"Token file not found: {self.token_path}")
            
            with open(self.token_path, 'r') as f:
                token_data = json.load(f)
            logger.info(f"✅ Loaded Google User Token from file: {self.token_path}")
            return token_data
        except Exception as e:
            logger.error(f"❌ Error loading token from file {self.token_path}: {e}")
            raise
    
    def _authenticate(self) -> None:
        """
        Authenticate with Google using user's token
        
        Raises:
            FileNotFoundError: If token or client secrets file not found
            RefreshError: If token refresh fails
        """
        try:
            # Load user credentials from token
            token_data = self._load_token_data()
            
            # Create credentials from token
            self.credentials = UserCredentials.from_authorized_user_info(token_data, self.SCOPES)
            
            # Refresh token if expired
            if self.credentials.expired and self.credentials.refresh_token:
                request = Request()
                self.credentials.refresh(request)
                logger.info(f"Token refreshed for {self.token_path}")
            
            # Build Gmail service
            self.service = googleapiclient.discovery.build('gmail', 'v1', credentials=self.credentials)
            logger.info(f"✅ Gmail service initialized")
        
        except FileNotFoundError as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
        
        except RefreshError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise
    
    def get_inbox_count(self) -> int:
        """
        Get count of unread emails in inbox
        
        Returns:
            int: Number of unread emails
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized")
                return 0
            
            results = self.service.users().labels().get(
                userId='me',
                id='INBOX'
            ).execute()
            
            unread_count = results.get('messagesUnread', 0)
            logger.info(f"Unread emails in inbox: {unread_count}")
            return unread_count
        
        except HttpError as e:
            logger.error(f"Error getting inbox count: {str(e)}")
            return 0
    
    def list_emails(self, query: str = "is:unread", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List emails matching query
        
        Args:
            query (str): Gmail search query (e.g., "is:unread", "from:example@gmail.com")
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of email dictionaries with id and snippet
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized")
                return []
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails matching query: {query}")
            
            emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
                
                emails.append({
                    'id': message['id'],
                    'from': headers.get('From', 'Unknown'),
                    'subject': headers.get('Subject', 'No Subject'),
                    'date': headers.get('Date', 'Unknown'),
                    'snippet': msg.get('snippet', '')
                })
            
            return emails
        
        except HttpError as e:
            logger.error(f"Error listing emails: {str(e)}")
            return []
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send an email via Gmail API
        
        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body (plain text)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized - cannot send email")
                return False
            
            if not to or not subject or body is None:
                logger.error(f"Invalid email parameters - to: {to}, subject: {subject}, body length: {len(body) if body else 0}")
                return False
            
            from email.mime.text import MIMEText
            
            # Create MIME message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {'raw': raw_message}
            
            logger.info(f"Attempting to send email to {to} with subject: {subject}")
            logger.debug(f"Email body length: {len(body)} characters")
            
            # Send email via Gmail API
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            # Verify result
            if result and 'id' in result:
                message_id = result['id']
                logger.info(
                    f"✅ Email successfully sent to {to} | "
                    f"Subject: {subject} | "
                    f"Message ID: {message_id}"
                )
                return True
            else:
                logger.error(f"Gmail API returned unexpected response: {result}")
                return False
        
        except HttpError as e:
            logger.error(f"❌ Gmail API HttpError when sending email: {str(e)}")
            logger.error(f"Error details: {e.content if hasattr(e, 'content') else 'No details'}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {str(e)}", exc_info=True)
            return False
    
    def get_email_body(self, message_id: str) -> str:
        """
        Get full email body
        
        Args:
            message_id (str): Gmail message ID
            
        Returns:
            str: Email body text
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized")
                return ""
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract body from message
            if 'parts' in message['payload']:
                parts = message['payload']['parts']
                data = parts[0]['body'].get('data', '')
            else:
                data = message['payload']['body'].get('data', '')
            
            if data:
                text = base64.urlsafe_b64decode(data).decode('utf-8')
                return text
            
            return ""
        
        except HttpError as e:
            logger.error(f"Error getting email body: {str(e)}")
            return ""
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark email as read
        
        Args:
            message_id (str): Gmail message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                logger.error("Gmail service not initialized")
                return False
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Email {message_id} marked as read")
            return True
        
        except HttpError as e:
            logger.error(f"Error marking email as read: {str(e)}")
            return False
