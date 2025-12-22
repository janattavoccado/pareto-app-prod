"""
Chatwoot API Client
Handles communication with Chatwoot API for sending messages back to conversations
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ChatwootClient:
    """
    Client for interacting with Chatwoot API
    Handles sending messages back to conversations
    """
    
    def __init__(self):
        """Initialize Chatwoot client with configuration from environment"""
        self.api_url = os.getenv("CHATWOOT_API_URL")
        self.access_key = os.getenv("CHATWOOT_ACCESS_KEY")
        self.account_id = os.getenv("CHATWOOT_ACCOUNT_ID")
        
        # Validate configuration
        if not all([self.api_url, self.access_key, self.account_id]):
            raise ValueError(
                "Chatwoot configuration incomplete. "
                "Ensure CHATWOOT_API_URL, CHATWOOT_ACCESS_KEY, and CHATWOOT_ACCOUNT_ID are set in .env"
            )
        
        # Setup headers for API requests
        self.headers = {
            "Content-Type": "application/json",
            "api_access_token": self.access_key,
        }
        
        logger.info(f"Chatwoot client initialized for account {self.account_id}")
    
    def send_message(
        self,
        conversation_id: int,
        message_text: str,
        message_type: str = "outgoing",
        private: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a message to a Chatwoot conversation
        
        Args:
            conversation_id (int): The Chatwoot conversation ID
            message_text (str): The message content to send
            message_type (str): Type of message - 'outgoing' for agent responses
            private (bool): Whether the message is private (internal note)
            
        Returns:
            dict: API response containing message details
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            # Construct API endpoint
            endpoint = (
                f"{self.api_url}/api/v1/accounts/{self.account_id}/"
                f"conversations/{conversation_id}/messages"
            )
            
            # Prepare payload
            payload = {
                "content": message_text,
                "message_type": message_type,
                "private": private,
            }
            
            logger.info(
                f"Sending message to Chatwoot | "
                f"Conversation: {conversation_id} | "
                f"Type: {message_type} | "
                f"Private: {private}"
            )
            
            # Make API request
            response = requests.post(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            
            # Handle response
            if response.status_code in [200, 201]:
                logger.info(f"Message sent successfully to conversation {conversation_id}")
                return {
                    "success": True,
                    "message_id": response.json().get("id"),
                    "data": response.json(),
                }
            else:
                error_msg = f"Chatwoot API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                }
        
        except requests.Timeout:
            error_msg = "Chatwoot API request timeout"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
        
        except requests.RequestException as e:
            error_msg = f"Chatwoot API request failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
        
        except Exception as e:
            error_msg = f"Unexpected error sending message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
            }
    
    def get_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get conversation details from Chatwoot
        
        Args:
            conversation_id (int): The Chatwoot conversation ID
            
        Returns:
            dict: Conversation details or error information
        """
        try:
            endpoint = (
                f"{self.api_url}/api/v1/accounts/{self.account_id}/"
                f"conversations/{conversation_id}"
            )
            
            response = requests.get(
                endpoint,
                headers=self.headers,
                timeout=10,
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get conversation: {response.status_code}",
                }
        
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def update_conversation_status(
        self,
        conversation_id: int,
        status: str,
    ) -> Dict[str, Any]:
        """
        Update conversation status in Chatwoot
        
        Args:
            conversation_id (int): The Chatwoot conversation ID
            status (str): New status - 'open', 'resolved', 'pending', 'snoozed'
            
        Returns:
            dict: API response
        """
        try:
            endpoint = (
                f"{self.api_url}/api/v1/accounts/{self.account_id}/"
                f"conversations/{conversation_id}"
            )
            
            payload = {"status": status}
            
            response = requests.patch(
                endpoint,
                json=payload,
                headers=self.headers,
                timeout=10,
            )
            
            if response.status_code == 200:
                logger.info(f"Conversation {conversation_id} status updated to {status}")
                return {
                    "success": True,
                    "data": response.json(),
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update status: {response.status_code}",
                }
        
        except Exception as e:
            logger.error(f"Error updating conversation status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }


# Create a singleton instance
_chatwoot_client = None


def get_chatwoot_client() -> ChatwootClient:
    """
    Get or create the Chatwoot client instance
    
    Returns:
        ChatwootClient: The Chatwoot API client
    """
    global _chatwoot_client
    if _chatwoot_client is None:
        _chatwoot_client = ChatwootClient()
    return _chatwoot_client
