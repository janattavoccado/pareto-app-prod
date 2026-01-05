import logging
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

from .google_email_client import GoogleEmailClient
from .user_manager_db_v2 import get_user_manager_db_v2
from .config_loader_v2 import get_google_user_token_by_phone

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class SendEmailRequest(BaseModel):
    """Structured email send request"""
    recipient_email: EmailStr
    subject: str
    body: str
    sender_email: Optional[EmailStr] = None
    
    class Config:
        str_strip_whitespace = True


class CheckUnreadRequest(BaseModel):
    """Structured unread email check request"""
    max_results: int = Field(default=5, ge=1, le=100)


class ListEmailsRequest(BaseModel):
    """Structured email list request"""
    query: str = Field(default="is:unread")
    max_results: int = Field(default=10, ge=1, le=100)


class ActionResult(BaseModel):
    """Generic action result"""
    success: bool
    action: str
    response: str
    executed: bool = False
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Email Action Executor
# ============================================================================

class EmailActionExecutor:
    """
    Executes email actions based on agent responses
    Parses agent responses and calls Gmail API
    """
    
    def __init__(self, phone_number: str):
        """
        Initialize executor with user's phone number
        
        Args:
            phone_number (str): User's phone number (session ID)
        """
        self.phone_number = phone_number
        self.user_manager = get_user_manager_db_v2()
        self.email_client = None
        self._initialize_email_client()
    
    def _initialize_email_client(self) -> None:
        """Initialize Gmail API client with user's credentials"""
        try:
            user_data = self.user_manager.get_user_by_phone(self.phone_number)
            
            if not user_data:
                logger.error(f"User not found: {self.phone_number}")
                return
            
            token = get_google_user_token_by_phone(self.phone_number)
            
            if not token:
                logger.error(f"No Google token for user: {self.phone_number}")
                return
            
            self.email_client = GoogleEmailClient(token)
            logger.info(f"Email client initialized for {self.phone_number}")
        
        except Exception as e:
            logger.error(f"Error initializing email client: {str(e)}")
    
    def _extract_text_from_response(self, response: Any) -> str:
        """
        Extract plain text from agent response
        Handles ModelResponse objects and other types
        
        Args:
            response: Agent response (could be ModelResponse, string, etc.)
            
        Returns:
            str: Plain text content
        """
        try:
            # If it's a ModelResponse object, extract text from output
            if hasattr(response, 'output'):
                output = response.output
                if isinstance(output, list) and len(output) > 0:
                    first_output = output[0]
                    # Extract text from ResponseOutputMessage
                    if hasattr(first_output, 'content'):
                        content = first_output.content
                        if isinstance(content, list) and len(content) > 0:
                            text_content = content[0]
                            if hasattr(text_content, 'text'):
                                return text_content.text
                            elif isinstance(text_content, dict) and 'text' in text_content:
                                return text_content['text']
                            else:
                                return str(text_content)
            
            # Fallback: convert to string
            return str(response)
        
        except Exception as e:
            logger.warning(f"Error extracting text from response: {str(e)}")
            return str(response)
    
    def _detect_action_type(self, response_text: str) -> str:
        """
        Detect the type of email action from response text
        
        Args:
            response_text (str): Agent response text
            
        Returns:
            str: Action type (send_email, check_unread, list_emails, etc.)
        """
        response_lower = response_text.lower()
        
        # IMPORTANT: Check for list/summarize keywords FIRST to avoid false positives
        # "summarize emails" should be list_emails, not send_email
        # Includes English, Swedish, and Croatian keywords
        list_keywords = [
            # English
            'summarize', 'summary', 'list', 'show', 'recent', 'latest',
            'last', 'my emails', 'my messages', 'get emails', 'retrieve',
            'fetch', 'read', 'what emails', 'any emails', 'new emails',
            # Swedish
            'sammanfatta', 'sammanfattning', 'visa', 'senaste', 'sista',
            'mina mejl', 'mina meddelanden', 'hämta mejl', 'läs',
            # Croatian (sažeti=summarize, prikazati=show, zadnji=last, moji=my)
            'sažeti', 'sažetak', 'popis', 'prikaži', 'nedavni', 'zadnji',
            'moji mailovi', 'moje poruke', 'dohvati mailove', 'čitaj'
        ]
        if any(keyword in response_lower for keyword in list_keywords):
            return 'list_emails'
        
        # Check for unread-specific keywords
        # Includes English, Swedish, and Croatian keywords
        unread_keywords = [
            # English
            'unread', 'inbox', 'check inbox', 'new messages',
            # Swedish
            'olästa', 'inkorg', 'kolla inkorg', 'nya meddelanden',
            # Croatian (nepročitano=unread, pristigla pošta=inbox)
            'nepročitano', 'pristigla pošta', 'provjeri pristiglu poštu', 'nove poruke'
        ]
        if any(keyword in response_lower for keyword in unread_keywords):
            return 'check_unread'
        
        # Check for send keywords LAST (most specific action)
        # Includes English, Swedish, and Croatian keywords
        send_keywords = [
            # English
            'send', 'sent', 'sending', 'email to', 'compose', 'write email',
            # Swedish
            'skicka', 'skickat', 'skickar', 'mejl till', 'skriv mejl',
            # Croatian (poslati=send, poslano=sent, e-mail=email)
            'poslati', 'poslano', 'šaljem', 'e-mail na', 'napiši e-mail', 'sastavi e-mail'
        ]
        if any(keyword in response_lower for keyword in send_keywords):
            return 'send_email'
        
        return 'unknown'
    
    def _parse_send_email_action(self, response_text: str) -> Optional[SendEmailRequest]:
        """
        Parse send email action from agent response
        
        Args:
            response_text (str): Agent response text
            
        Returns:
            SendEmailRequest or None if parsing fails
        """
        try:
            logger.info(f"Parsing send email action from: {response_text[:100]}...")
            
            # Get user email as default sender
            user_data = self.user_manager.get_user_by_phone(self.phone_number)
            default_sender = user_data.get("email") if user_data else None
            
            # Extract recipient email
            recipient_match = re.search(
                r'(?:to|recipient|email to|send to)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                response_text,
                re.IGNORECASE
            )
            recipient = recipient_match.group(1) if recipient_match else None
            
            if not recipient:
                logger.warning("Could not extract recipient email")
                return None
            
            logger.info(f"Extracted recipient: {recipient}")
            
            # Extract sender (optional)
            sender_match = re.search(
                r'(?:from|sender)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                response_text,
                re.IGNORECASE
            )
            sender = sender_match.group(1) if sender_match else default_sender
            
            if sender:
                logger.info(f"Extracted sender: {sender}")
            else:
                logger.info("Extracted sender: None")
            
            # Extract subject - try multiple patterns
            subject = None
            subject_patterns = [
                r'(?:subject|subject:)\s*["\']?([^"\']\n]+)["\']?(?:\s|$)',
                r'subject:\s*([^\n]+)',
                r'with subject\s+["\']?([^"\']\n]+)["\']?',
                r'subject\s+["\']?([^"\']\n]+)["\']?',
            ]
            
            for pattern in subject_patterns:
                subject_match = re.search(pattern, response_text, re.IGNORECASE)
                if subject_match:
                    subject = subject_match.group(1).strip()
                    if subject:
                        break
            
            if not subject:
                logger.warning("Could not extract subject")
                subject = "No Subject"
            else:
                logger.info(f"Extracted subject: {subject}")
            
            # Extract body - try multiple patterns
            body = None
            body_patterns = [
                r'(?:content|body|message):\s*["\']?([^"\']\n]+)["\']?(?:\s|$)',
                r'content:\s*([^\n]+)',
                r'body:\s*([^\n]+)',
                r'message:\s*([^\n]+)',
                r'and content:\s*([^\n]+)',
                r'and body:\s*([^\n]+)',
                r'with content\s+["\']?([^"\']\n]+)["\']?',
            ]
            
            for pattern in body_patterns:
                body_match = re.search(pattern, response_text, re.IGNORECASE)
                if body_match:
                    body = body_match.group(1).strip()
                    if body:
                        break
            
            if not body:
                logger.warning("Could not extract body, using empty body")
                body = ""
            else:
                logger.info(f"Extracted body: {body[:50]}...")
            
            # Create and validate request
            send_request = SendEmailRequest(
                recipient_email=recipient,
                subject=subject,
                body=body,
                sender_email=sender
            )
            
            return send_request
        
        except Exception as e:
            logger.error(f"Error parsing send email action: {str(e)}")
            return None
    
    def execute_send_email(self, request: SendEmailRequest) -> ActionResult:
        """
        Execute send email action
        
        Args:
            request (SendEmailRequest): Email send request
            
        Returns:
            ActionResult: Execution result
        """
        try:
            if not self.email_client:
                logger.error("Email client not initialized")
                return ActionResult(
                    success=False,
                    action="send_email",
                    response="❌ Email client not initialized",
                    executed=False
                )
            
            # Send email
            success = self.email_client.send_email(
                to=request.recipient_email,
                subject=request.subject,
                body=request.body
            )
            
            if success:
                response = (
                    f"✅ Email sent successfully to {request.recipient_email} "
                    f"with subject: {request.subject}"
                )
                logger.info(response)
                return ActionResult(
                    success=True,
                    action="send_email",
                    response=response,
                    executed=True,
                    data={
                        "recipient": request.recipient_email,
                        "subject": request.subject,
                        "body_length": len(request.body)
                    }
                )
            else:
                response = f"❌ Failed to send email to {request.recipient_email}"
                logger.error(response)
                return ActionResult(
                    success=False,
                    action="send_email",
                    response=response,
                    executed=False
                )
        
        except Exception as e:
            logger.error(f"Error executing send email: {str(e)}")
            return ActionResult(
                success=False,
                action="send_email",
                response=f"❌ Error: {str(e)}",
                executed=False
            )
    
    def execute_action(self, response: Any) -> ActionResult:
        """
        Execute action based on agent response
        
        Args:
            response: Agent response (ModelResponse, string, etc.)
            
        Returns:
            ActionResult: Execution result
        """
        try:
            # Extract text from response
            response_text = self._extract_text_from_response(response)
            logger.info(f"Extracted response text: {response_text[:100]}...")
            
            # Detect action type
            action_type = self._detect_action_type(response_text)
            logger.info(f"Detected action type: {action_type}")
            
            # Execute appropriate action
            if action_type == 'send_email':
                send_request = self._parse_send_email_action(response_text)
                
                if send_request:
                    return self.execute_send_email(send_request)
                else:
                    return ActionResult(
                        success=False,
                        action="send_email",
                        response="❌ Could not parse email send request",
                        executed=False
                    )
            
            elif action_type == 'list_emails':
                return self.execute_list_emails(response_text)
            
            elif action_type == 'check_unread':
                return self.execute_check_unread()
            
            else:
                return ActionResult(
                    success=False,
                    action=action_type,
                    response=f"❌ Action type '{action_type}' not yet implemented",
                    executed=False
                )
        
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}", exc_info=True)
            return ActionResult(
                success=False,
                action="unknown",
                response=f"❌ Error: {str(e)}",
                executed=False
            )

    def execute_list_emails(self, response_text: str) -> ActionResult:
        """
        Execute list emails action - retrieves and summarizes recent emails
        
        Args:
            response_text (str): Original response text (used to determine count)
            
        Returns:
            ActionResult: Execution result with email summaries
        """
        try:
            if not self.email_client:
                logger.error("Email client not initialized")
                return ActionResult(
                    success=False,
                    action="list_emails",
                    response="❌ Email client not initialized. Please connect your email account.",
                    executed=False
                )
            
            # Determine how many emails to fetch (default 5, max 10)
            import re
            count_match = re.search(r'(\d+)\s*(?:emails?|messages?)', response_text.lower())
            max_results = int(count_match.group(1)) if count_match else 5
            max_results = min(max_results, 10)  # Cap at 10
            
            logger.info(f"Fetching {max_results} recent emails")
            
            # Fetch recent emails
            emails = self.email_client.list_emails(query="", max_results=max_results)
            
            if not emails:
                return ActionResult(
                    success=True,
                    action="list_emails",
                    response="📧 No recent emails found in your inbox.",
                    executed=True,
                    data={"count": 0, "emails": []}
                )
            
            # Format email summaries with content snippets
            email_summaries = []
            for i, email in enumerate(emails, 1):
                sender = email.get('from', 'Unknown')
                # Extract just the name part if it's in "Name <email>" format
                if '<' in sender:
                    sender_name = sender.split('<')[0].strip().strip('"')
                    if not sender_name:
                        sender_name = sender.split('<')[1].split('>')[0]
                else:
                    sender_name = sender
                # Truncate long sender names
                if len(sender_name) > 35:
                    sender_name = sender_name[:32] + "..."
                
                subject = email.get('subject', 'No Subject')
                if len(subject) > 60:
                    subject = subject[:57] + "..."
                
                # Include snippet (preview of email content)
                snippet = email.get('snippet', '')
                if snippet:
                    # Clean up snippet - remove extra whitespace
                    snippet = ' '.join(snippet.split())
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    snippet_line = f"\n   📝 _{snippet}_"
                else:
                    snippet_line = ""
                
                # Get date if available
                date = email.get('date', '')
                date_str = ""
                if date:
                    try:
                        # Parse and format date nicely
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(date)
                        date_str = f" ({dt.strftime('%d %b %H:%M')})"
                    except:
                        pass
                
                email_summaries.append(
                    f"{i}. *{subject}*{date_str}\n   👤 From: {sender_name}{snippet_line}"
                )
            
            response_msg = f"📧 *Your {len(emails)} most recent emails:*\n\n" + "\n\n".join(email_summaries)
            
            logger.info(f"Successfully retrieved {len(emails)} emails")
            return ActionResult(
                success=True,
                action="list_emails",
                response=response_msg,
                executed=True,
                data={"count": len(emails), "emails": emails}
            )
        
        except Exception as e:
            logger.error(f"Error listing emails: {str(e)}", exc_info=True)
            return ActionResult(
                success=False,
                action="list_emails",
                response=f"❌ Error retrieving emails: {str(e)}",
                executed=False
            )
    
    def execute_check_unread(self) -> ActionResult:
        """
        Execute check unread emails action
        
        Returns:
            ActionResult: Execution result with unread count and summaries
        """
        try:
            if not self.email_client:
                logger.error("Email client not initialized")
                return ActionResult(
                    success=False,
                    action="check_unread",
                    response="❌ Email client not initialized. Please connect your email account.",
                    executed=False
                )
            
            # Get unread count
            unread_count = self.email_client.get_inbox_count()
            
            # Fetch unread emails
            unread_emails = self.email_client.list_emails(query="is:unread", max_results=5)
            
            if unread_count == 0:
                return ActionResult(
                    success=True,
                    action="check_unread",
                    response="✅ You have no unread emails. Your inbox is clear!",
                    executed=True,
                    data={"unread_count": 0, "emails": []}
                )
            
            # Format unread email summaries
            email_summaries = []
            for i, email in enumerate(unread_emails, 1):
                sender = email.get('from', 'Unknown')
                if len(sender) > 40:
                    sender = sender[:37] + "..."
                subject = email.get('subject', 'No Subject')
                if len(subject) > 50:
                    subject = subject[:47] + "..."
                
                email_summaries.append(f"{i}. *From:* {sender}\n   *Subject:* {subject}")
            
            if unread_count > 5:
                response_msg = f"📬 *You have {unread_count} unread emails.* Here are the 5 most recent:\n\n" + "\n\n".join(email_summaries)
            else:
                response_msg = f"📬 *You have {unread_count} unread email(s):*\n\n" + "\n\n".join(email_summaries)
            
            logger.info(f"Successfully checked unread emails: {unread_count} unread")
            return ActionResult(
                success=True,
                action="check_unread",
                response=response_msg,
                executed=True,
                data={"unread_count": unread_count, "emails": unread_emails}
            )
        
        except Exception as e:
            logger.error(f"Error checking unread emails: {str(e)}", exc_info=True)
            return ActionResult(
                success=False,
                action="check_unread",
                response=f"❌ Error checking unread emails: {str(e)}",
                executed=False
            )
