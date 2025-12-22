"""
Mail Me Command Handler
Handles "mail me" commands to send structured emails to user's own email address

File location: pareto_agents/mail_me_handler.py
"""

import logging
import re
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field, EmailStr

logger = logging.getLogger(__name__)


class MailMeRequest(BaseModel):
    """Structured request for mail me command"""
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    sender_email: EmailStr = Field(..., description="Sender email address")
    subject: str = Field(..., description="Email subject", min_length=1, max_length=200)
    body: str = Field(..., description="Email body/content", min_length=1)
    user_name: str = Field(..., description="User's name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "recipient_email": "jan@example.com",
                "sender_email": "jan@example.com",
                "subject": "Eastern wall painting and western wall plaster work",
                "body": "Work needed:\n- Eastern wall needs to be painted\n- Western wall needs plaster\n\nEstimates:\n- Time: 2 working days\n- Cost: 400 euros",
                "user_name": "Jan Nylen"
            }
        }


class MailMeHandler:
    """
    Handles "mail me" commands
    Parses message content and creates structured emails
    """
    
    @staticmethod
    def is_mail_me_command(message: str) -> bool:
        """
        Check if message starts with "mail me" command
        
        Args:
            message (str): User's message
            
        Returns:
            bool: True if message is a mail me command
        """
        return message.strip().lower().startswith("mail me")
    
    @staticmethod
    def extract_mail_me_content(message: str) -> str:
        """
        Extract content after "mail me" command
        
        Args:
            message (str): User's message starting with "mail me"
            
        Returns:
            str: Content to be mailed
        """
        # Remove "mail me" prefix (case-insensitive)
        content = re.sub(r'^mail\s+me\s+', '', message, flags=re.IGNORECASE).strip()
        return content
    
    @staticmethod
    def generate_subject_from_content(content: str, max_length: int = 100) -> str:
        """
        Generate a structured subject line from message content
        
        Extracts key information and creates a concise subject
        
        Args:
            content (str): Message content
            max_length (int): Maximum subject length
            
        Returns:
            str: Generated subject line
        """
        # Remove extra whitespace and newlines
        content = ' '.join(content.split())
        
        # Try to extract key phrases
        # Look for work items, tasks, or main topics
        
        # Pattern 1: Look for "X need to be Y" patterns
        work_patterns = re.findall(
            r'([^.,]+?)\s+need(?:s)?\s+(?:to\s+)?(?:be\s+)?([^.,]+)',
            content,
            re.IGNORECASE
        )
        
        if work_patterns:
            # Use first work item as subject
            item, action = work_patterns[0]
            subject = f"{item.strip()} - {action.strip()}"
        else:
            # Fallback: use first sentence or first 100 chars
            sentences = re.split(r'[.!?]', content)
            subject = sentences[0].strip() if sentences[0] else content[:100]
        
        # Truncate if too long
        if len(subject) > max_length:
            subject = subject[:max_length].rsplit(' ', 1)[0] + '...'
        
        return subject
    
    @staticmethod
    def structure_email_body(content: str) -> str:
        """
        Structure email body from message content
        
        Organizes content into sections for better readability
        
        Args:
            content (str): Raw message content
            
        Returns:
            str: Structured email body
        """
        # Split by common delimiters
        lines = content.split('\n')
        
        # Group related information
        work_items = []
        estimates = []
        other_info = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect work items (contain "need", "require", "should")
            if any(keyword in line.lower() for keyword in ['need', 'require', 'should', 'must']):
                work_items.append(f"• {line}")
            
            # Detect estimates (contain "time", "cost", "price", "day", "hour", "euro", "$")
            elif any(keyword in line.lower() for keyword in ['time', 'cost', 'price', 'day', 'hour', 'euro', '$', '€']):
                estimates.append(f"• {line}")
            
            # Other information
            else:
                other_info.append(f"• {line}")
        
        # Build structured body
        body_parts = []
        
        if work_items:
            body_parts.append("**Work Items:**")
            body_parts.extend(work_items)
            body_parts.append("")
        
        if estimates:
            body_parts.append("**Estimates:**")
            body_parts.extend(estimates)
            body_parts.append("")
        
        if other_info:
            body_parts.append("**Additional Information:**")
            body_parts.extend(other_info)
        
        body = "\n".join(body_parts)
        
        # If no structure detected, return original with formatting
        if not body_parts or not body.strip():
            body = content
        
        return body
    
    @staticmethod
    def create_mail_me_request(
        content: str,
        user_email: str,
        user_name: str
    ) -> MailMeRequest:
        """
        Create a structured MailMeRequest from message content
        
        Args:
            content (str): Message content (after "mail me" prefix)
            user_email (str): User's email address (from users.json)
            user_name (str): User's full name (from users.json)
            
        Returns:
            MailMeRequest: Structured email request
            
        Raises:
            ValueError: If request cannot be created
        """
        try:
            # Generate subject from content
            subject = MailMeHandler.generate_subject_from_content(content)
            
            # Structure email body
            body = MailMeHandler.structure_email_body(content)
            
            # Create request
            request = MailMeRequest(
                recipient_email=user_email,
                sender_email=user_email,
                subject=subject,
                body=body,
                user_name=user_name
            )
            
            logger.info(
                f"Created mail me request for {user_name} | "
                f"Subject: {subject} | Body length: {len(body)}"
            )
            
            return request
        
        except Exception as e:
            logger.error(f"Error creating mail me request: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def format_mail_me_response(user_name: str, subject: str, recipient: str) -> str:
        """
        Format response message for mail me command
        
        Args:
            user_name (str): User's name
            subject (str): Email subject
            recipient (str): Recipient email
            
        Returns:
            str: Formatted response
        """
        return (
            f"✅ **Email Sent Successfully**\n\n"
            f"**To:** {user_name} ({recipient})\n"
            f"**Subject:** {subject}\n\n"
            f"Your message has been structured and sent to your email address."
        )


# Example usage
if __name__ == "__main__":
    # Test mail me handler
    test_message = "mail me the eastern wall need to be painted and western wall need plaster. Estimates time needed 2 working days, cost is 400 euros."
    
    if MailMeHandler.is_mail_me_command(test_message):
        content = MailMeHandler.extract_mail_me_content(test_message)
        print(f"Content: {content}\n")
        
        subject = MailMeHandler.generate_subject_from_content(content)
        print(f"Subject: {subject}\n")
        
        body = MailMeHandler.structure_email_body(content)
        print(f"Body:\n{body}\n")
        
        request = MailMeHandler.create_mail_me_request(
            content,
            "jan@example.com",
            "Jan Nylen"
        )
        print(f"Request: {request}")
