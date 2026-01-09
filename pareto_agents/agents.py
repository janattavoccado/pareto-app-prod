"""
Pareto Agents - OpenAI Agents SDK Integration for Pareto
Updated with improved routing logic for Email, Calendar, Personal Assistant, and CRM agents

File location: pareto_agents/agents.py
"""

import logging
import asyncio
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import pytz

from agents import Agent, Runner
from .mail_me_handler import MailMeHandler
from .memory_service import get_memory_service, add_conversation_memory, get_memory_context

logger = logging.getLogger(__name__)

# Default timezone for the application
DEFAULT_TIMEZONE = pytz.timezone('Europe/Stockholm')  # CET/CEST


def get_current_datetime_context() -> str:
    """
    Get the current date and time formatted for agent context.
    Returns a string with current date, time, and day of week.
    """
    now = datetime.now(DEFAULT_TIMEZONE)
    return (
        f"Current date and time: {now.strftime('%A, %d %B %Y at %H:%M')} "
        f"(Timezone: {DEFAULT_TIMEZONE.zone}). "
        f"Today is {now.strftime('%A')}. "
        f"Tomorrow is {(now + __import__('datetime').timedelta(days=1)).strftime('%A, %d %B %Y')}."
    )


# ============================================================================
# Agent Definitions
# ============================================================================

# Email Management Agent - For direct email actions (send, compose)
email_agent = Agent(
    name="Email Manager",
    handoff_description="Specialist agent for email management tasks like sending emails",
    instructions=(
        "You are an email management assistant. You help users with email-related tasks. "
        "You can help with tasks like: "
        "1. Sending emails - compose and send emails to specified recipients "
        "2. Composing drafts - create email drafts for review "
        "\n"
        "IMPORTANT: When a user asks you to send an email, SEND IT IMMEDIATELY without asking for confirmation. "
        "Extract the recipient, subject, and body from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action."
    ),
)

# Calendar Management Agent - For direct calendar actions (book, create, update, delete)
calendar_agent = Agent(
    name="Calendar Manager",
    handoff_description="Specialist agent for calendar actions like booking meetings",
    instructions=(
        "You are a calendar management assistant. You help users manage their Google Calendar. "
        "You can help with tasks like: "
        "1. Creating new events and meetings - schedule events with date, time, location, attendees "
        "2. Updating existing events - modify event details, reschedule meetings "
        "3. Deleting events - cancel meetings and remove events from calendar "
        "\n"
        "CRITICAL: The message will contain a [SYSTEM: ...] section with the CURRENT DATE AND TIME. "
        "You MUST use this date/time information to correctly interpret relative dates like 'tomorrow', 'next Monday', 'today'. "
        "NEVER guess or hallucinate dates - always calculate from the provided current date. "
        "\n"
        "IMPORTANT: When a user asks you to create or modify a calendar event, PROCEED IMMEDIATELY without asking for confirmation. "
        "Extract the event details (title, date, time, location, attendees) from the user's request and proceed directly. "
        "Provide a confirmation message after the action is completed with the EXACT date you scheduled it for. "
        "Be direct and action-oriented. Do not ask for confirmation - just execute the requested action. "
        "\n"
        "Always format times in 24-hour format and include the full date (day, month, year) in responses."
    ),
)

# Personal Assistant Agent - For queries, summaries, and general conversation
personal_assistant_agent = Agent(
    name="Personal Assistant",
    handoff_description="Specialist agent for queries, summaries, and general assistance",
    instructions=(
        "You are a helpful personal assistant with MEMORY capabilities. You help users with: "
        "1. Calendar queries - 'What meetings do I have today?', 'Show my schedule for tomorrow' "
        "2. Email queries - 'Summarize my unread emails', 'What new emails do I have?' "
        "3. Daily summaries - 'Give me a summary of my day', 'What's on my agenda?' "
        "4. General conversation - Greetings, questions, and general assistance "
        "5. Date and time questions - 'What is today's date?', 'What time is it?' "
        "6. CRM operations - Store information to CRM, retrieve leads from CRM "
        "\n"
        "CRITICAL: The message will contain a [SYSTEM: ...] section with the CURRENT DATE AND TIME. "
        "When a user asks about the current date, time, or day of week, use this information to provide an accurate answer. "
        "\n"
        "MEMORY RULES - VERY IMPORTANT: "
        "1. If the message contains a [MEMORY: ...] section, ONLY use facts that are EXPLICITLY stated in that section. "
        "2. DO NOT invent, guess, or hallucinate any information about the user that is not in the memory section. "
        "3. If the user asks about something not in your memory, say 'I don't have that information stored yet' or 'I don't recall that detail'. "
        "4. NEVER make up names, companies, contacts, or any personal details that are not explicitly provided. "
        "5. When recalling information, only state what you are 100% certain is in the memory - nothing more. "
        "6. It's better to say 'I don't know' than to provide incorrect information. "
        "\n"
        "When a user asks about their calendar or emails, retrieve the relevant information and present it clearly. "
        "For greetings like 'Hello', respond warmly and ask how you can help. "
        "Be friendly, helpful, and honest about what you do and don't know."
    ),
)


# ============================================================================
# Message Classification
# ============================================================================

def classify_message(message: str) -> str:
    """
    Classify the message to determine which agent should handle it.

    Returns:
        str: One of 'help', 'mail_me', 'calendar_action', 'email_action', 'crm_store', 'crm_read', 'personal_assistant'
    """
    message_lower = message.lower().strip()

    # 0. Check for HELP command (highest priority)
    # Matches: "help", "pareto --help", "pareto -help", "pareto help", "--help", "-help"
    help_patterns = [
        r'^help$',  # Just "help"
        r'^pareto\s*[-]+\s*help$',  # "pareto --help", "pareto -help"
        r'^pareto\s+help$',  # "pareto help"
        r'^[-]+help$',  # "--help", "-help"
        r'^hjälp$',  # Swedish: "hjälp"
        r'^pomoć$',  # Croatian: "pomoć"
    ]
    for pattern in help_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched help pattern: {pattern}")
            return 'help'

    # 1. Check for 'mail me' command (highest priority)
    if MailMeHandler.is_mail_me_command(message):
        return 'mail_me'

    # 2. Check for CRM STORE commands (store, save, add to CRM)
    # Includes English, Swedish, and Croatian keywords
    crm_store_patterns = [
        # English patterns
        r'\b(store|save|add|put|log|record)\b.*(in|to|into)\s*(the\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(store|save|add|put|log|record)',
        r'\badd\s+(this\s+)?(to\s+)?(my\s+)?(crm|c\.r\.m\.)',
        r'\bsave\s+(this\s+)?(to\s+)?(my\s+)?(crm|c\.r\.m\.)',
        r'\bstore\s+(this\s+)?(in\s+)?(my\s+)?(crm|c\.r\.m\.)',
        r'\blog\s+(this\s+)?(in|to)\s+(my\s+)?(crm|c\.r\.m\.)',
        # Swedish patterns (spara=save, lägg till=add, lagra=store)
        r'\b(spara|lägg till|lagra|registrera)\b.*(i|till)\s*(min\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(spara|lägg|lagra)',
        r'\bspara\s+(detta\s+)?(i\s+)?(min\s+)?(crm|c\.r\.m\.)',
        # Croatian patterns (spremi=save, dodaj=add, pohrani=store)
        r'\b(spremi|dodaj|pohrani|zabilježi)\b.*(u|na)\s*(moj\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(spremi|dodaj|pohrani)',
        r'\bspremi\s+(ovo\s+)?(u\s+)?(moj\s+)?(crm|c\.r\.m\.)',
    ]

    for pattern in crm_store_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched CRM store pattern: {pattern}")
            return 'crm_store'

    # 3. Check for CRM READ commands (read, get, show, list from CRM)
    # Includes English, Swedish, and Croatian keywords
    crm_read_patterns = [
        # English patterns - standard
        r'\b(read|get|show|list|display|fetch|retrieve|view)\b.*(from|in)\s*(the\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(read|get|show|list|display|fetch|retrieve|view|leads?|data|items?)',
        r'\b(my|the)\s+(crm|c\.r\.m\.)\s*(leads?|data|entries|records|items?)?',
        r'\bshow\s+(me\s+)?(my\s+)?(crm|c\.r\.m\.)',
        r'\bwhat.*(in|on)\s+(my\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\s*(leads?|status|summary|overview|items?|content)',
        r'\bleads?\s+(from|in)\s+(my\s+)?(crm|c\.r\.m\.)',
        # English patterns - "get me CRM", "show me CRM", etc.
        r'\b(get|show|read|fetch|give)\s+me\s+(the\s+)?(my\s+)?(crm|c\.r\.m\.)',
        r'\b(get|show|read|fetch)\s+(me\s+)?(my\s+)?(crm|c\.r\.m\.)\s*(content|data|leads?|items?)?',
        # English patterns - flexible (catch "from CRM..." at start or anywhere)
        r'^from\s+(the\s+)?(crm|c\.r\.m\.)',  # Message starting with "from CRM"
        r'\bfrom\s+(my\s+)?(crm|c\.r\.m\.)\b',  # "from my CRM" anywhere
        r'\b(crm|c\.r\.m\.)\s+(with|items?|entries|priority)',  # "CRM with...", "CRM items"
        r'\b(high|mid|medium|low)\s+priority.*(crm|c\.r\.m\.)',  # "high priority CRM"
        r'\b(crm|c\.r\.m\.).*(high|mid|medium|low)\s+priority',  # "CRM... high priority"
        r'\b(open|closed|progress).*(crm|c\.r\.m\.)',  # "open CRM leads"
        r'\b(crm|c\.r\.m\.).*(open|closed|progress)',  # "CRM open leads"
        # Swedish patterns (visa=show, hämta=get/fetch, läs=read)
        r'\b(visa|hämta|läs|lista)\b.*(från|i)\s*(min\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(visa|hämta|läs|lista|leads?)',
        r'\bvisa\s+(mig\s+)?(min\s+)?(crm|c\.r\.m\.)',
        r'\bvad.*(i|på)\s+(min\s+)?(crm|c\.r\.m\.)',
        r'^från\s+(min\s+)?(crm|c\.r\.m\.)',  # Swedish: "från CRM" at start
        # Croatian patterns (prikaži=show, dohvati=get/fetch, pročitaj=read)
        r'\b(prikaži|dohvati|pročitaj|izlistaj)\b.*(iz|u)\s*(moj\s+)?(crm|c\.r\.m\.)',
        r'\b(crm|c\.r\.m\.)\b.*(prikaži|dohvati|pročitaj|izlistaj|leads?)',
        r'\bprikaži\s+(mi\s+)?(moj\s+)?(crm|c\.r\.m\.)',
        r'\bšto.*(u|na)\s+(mom\s+)?(crm|c\.r\.m\.)',
        r'^iz\s+(mog\s+)?(crm|c\.r\.m\.)',  # Croatian: "iz CRM" at start
    ]

    for pattern in crm_read_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched CRM read pattern: {pattern}")
            return 'crm_read'

    # 4. Check for direct calendar ACTIONS (booking, creating, updating, deleting)
    # Includes English, Swedish, and Croatian keywords for multilingual support
    calendar_action_patterns = [
        # English patterns
        r'\b(book|schedule|create|set up|arrange)\b.*(meeting|appointment|event|call)',
        r'\b(update|change|modify|reschedule|move)\b.*(meeting|appointment|event)',
        r'\b(delete|cancel|remove)\b.*(meeting|appointment|event)',
        r'\badd\b.*(to|on).*(calendar|schedule)',
        r'\bbook me\b',
        r'\bschedule me\b',
        # Swedish patterns (boka=book, möte=meeting, kalender=calendar, avboka=cancel)
        # Note: Whisper sometimes transcribes "boka" as "boken" or "bokar"
        r'\b(boka|bokar|boken|skapa|lägg till|arrangera|planera)\b.*(möte|möten|händelse|samtal|event)',
        r'\b(ändra|flytta|uppdatera|byt)\b.*(möte|möten|händelse)',
        r'\b(avboka|ta bort|radera|ställ in)\b.*(möte|möten|händelse)',
        r'\blägg\b.*(i|på).*(kalender|kalendern|schema)',
        r'\b(boka|bokar|boken)\s+(ett\s+)?möte\b',
        r'\b(ett\s+)?möte\b.*(imorgon|idag|nästa|klockan)',
        r'\bmöte\b.*(klockan|\d{1,2}[:.\s]?\d{0,2}\s*(am|pm)?|imorgon|idag)',
        # Croatian patterns (zakazati/rezervirati=book, sastanak=meeting, kalendar=calendar, otkazati=cancel)
        # Note: Whisper may transcribe variations like "zakaži", "rezerviraj", "zakažem"
        r'\b(zakazati|zakaži|zakažem|rezervirati|rezerviraj|stvoriti|stvori|napraviti|napravi|dogovoriti|dogovori)\b.*(sastanak|sastanke|događaj|poziv)',
        r'\b(promijeniti|promijeni|ažurirati|ažuriraj|premjestiti|premjesti)\b.*(sastanak|sastanke|događaj)',
        r'\b(otkazati|otkaži|obrisati|obriši|ukloniti|ukloni)\b.*(sastanak|sastanke|događaj)',
        r'\bdodaj\b.*(u|na).*(kalendar|raspored)',
        r'\b(zakazati|zakaži|rezervirati|rezerviraj)\s+(jedan\s+)?sastanak\b',
        r'\b(jedan\s+)?sastanak\b.*(sutra|danas|sljedeći|u)',
        # Flexible pattern: any message containing "sastanak" + time indicators
        r'\bsastanak\b.*(u|sati|\d{1,2}[:.\s]?\d{0,2}|sutra|danas)',
    ]

    for pattern in calendar_action_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched calendar action pattern: {pattern}")
            return 'calendar_action'

    # 5. Check for direct email ACTIONS (sending, composing)
    # Includes English, Swedish, and Croatian keywords for multilingual support
    email_action_patterns = [
        # English patterns
        r'\b(send|compose|write|draft)\b.*(email|mail|message)',
        r'\bemail\b.*(to|about)',
        r'\bsend\b.*(to)\b',
        # Swedish patterns (skicka=send, mejl/mail/e-post=email, meddelande=message)
        r'\b(skicka|skriv|författa)\b.*(mejl|mail|e-post|epost|meddelande)',
        r'\bmejla\b.*(till|om)',
        r'\bskicka\b.*(till)\b',
        # Croatian patterns (poslati=send, e-mail/mail/poruka=email/message)
        r'\b(poslati|pošalji|pošaljite|napisati|napiši|napišite|sastaviti|sastavi)\b.*(e-mail|email|mail|poruku|poruka)',
        r'\bmejlati\b.*(na|o)',
        r'\bposlati\b.*(na)\b',
    ]

    for pattern in email_action_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"[classify] Matched email action pattern: {pattern}")
            return 'email_action'

    # 6. Everything else goes to Personal Assistant (queries, summaries, greetings)
    # This includes:
    # - "What meetings do I have today?"
    # - "Summarize my emails"
    # - "Hello"
    # - "Show my schedule"
    # - "What's on my agenda?"
    # - General questions

    return 'personal_assistant'


# ============================================================================
# CRM Helper Functions
# ============================================================================

def extract_crm_content(message: str) -> str:
    """
    Extract the content to store in CRM from the message.
    Removes the CRM command prefix to get the actual content.
    
    Args:
        message: The full user message
        
    Returns:
        str: The content to store (without CRM command prefix)
    """
    # Patterns to remove from the beginning
    prefixes_to_remove = [
        # English
        r'^(store|save|add|put|log|record)\s+(this\s+)?(in|to|into)\s+(the\s+)?(my\s+)?(crm|c\.r\.m\.)\s*[:\-]?\s*',
        r'^(add|save|store|log)\s+(to\s+)?(my\s+)?(crm|c\.r\.m\.)\s*[:\-]?\s*',
        r'^(crm|c\.r\.m\.)\s*[:\-]?\s*(store|save|add)\s*[:\-]?\s*',
        # Swedish
        r'^(spara|lägg till|lagra|registrera)\s+(detta\s+)?(i|till)\s+(min\s+)?(crm|c\.r\.m\.)\s*[:\-]?\s*',
        r'^(crm|c\.r\.m\.)\s*[:\-]?\s*(spara|lägg)\s*[:\-]?\s*',
        # Croatian
        r'^(spremi|dodaj|pohrani|zabilježi)\s+(ovo\s+)?(u|na)\s+(moj\s+)?(crm|c\.r\.m\.)\s*[:\-]?\s*',
        r'^(crm|c\.r\.m\.)\s*[:\-]?\s*(spremi|dodaj)\s*[:\-]?\s*',
    ]
    
    content = message.strip()
    
    for pattern in prefixes_to_remove:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    return content.strip()


def format_leads_for_response(leads: List[Any], include_details: bool = False) -> str:
    """
    Format CRM leads into a readable response for the user.
    
    Args:
        leads: List of CRMLead objects
        include_details: Whether to include full details or just summary
        
    Returns:
        str: Formatted response string
    """
    if not leads:
        return "📋 You don't have any leads in your CRM yet."
    
    response_parts = [f"📋 **Your CRM Leads** ({len(leads)} total):\n"]
    
    for i, lead in enumerate(leads, 1):
        priority_emoji = {
            'High': '🔴',
            'Mid': '🟡',
            'Low': '🟢'
        }.get(lead.priority, '⚪')
        
        status_emoji = {
            'Open': '📬',
            'In Progress': '⏳',
            'Closed': '✅',
            'Rejected': '❌'
        }.get(lead.status, '📄')
        
        lead_line = f"\n{i}. {priority_emoji} **{lead.lead_subject}**"
        lead_line += f"\n   {status_emoji} Status: {lead.status} | Owner: {lead.owner}"
        
        if lead.created_at:
            lead_line += f"\n   📅 Created: {lead.created_at.strftime('%Y-%m-%d %H:%M')}"
        
        if include_details and lead.lead_content:
            try:
                content = json.loads(lead.lead_content) if isinstance(lead.lead_content, str) else lead.lead_content
                if content.get('summary'):
                    lead_line += f"\n   📝 {content['summary'][:100]}..."
            except:
                pass
        
        response_parts.append(lead_line)
    
    return "\n".join(response_parts)


async def handle_crm_store(message: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle CRM store command - extract content and store as a new lead.
    
    Args:
        message: The user's message
        user_data: User information from database
        
    Returns:
        dict: Processing result
    """
    from pareto_agents.database import get_db_manager
    from pareto_agents.crm_service import CRMService
    
    try:
        # Extract the content to store (remove CRM command prefix)
        content_to_store = extract_crm_content(message)
        
        if not content_to_store or len(content_to_store) < 5:
            return {
                "is_mail_me": False,
                "agent_response": "❌ Please provide some content to store in CRM. For example: 'Store in CRM: New lead from TechCorp interested in our services'",
                "action_type": "crm_store",
                "success": False
            }
        
        # Get user info
        tenant_id = user_data.get('tenant_id')
        user_id = user_data.get('id')
        user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        
        if not tenant_id or not user_id:
            return {
                "is_mail_me": False,
                "agent_response": "❌ Unable to identify your tenant. Please contact support.",
                "action_type": "crm_store",
                "success": False
            }
        
        # Create the lead using CRM service
        db_manager = get_db_manager()
        db_session = db_manager.get_session()
        
        try:
            crm_service = CRMService(db_session)
            lead = crm_service.create_lead(
                message=content_to_store,
                tenant_id=tenant_id,
                user_id=user_id
            )
            
            # Format success response
            priority_emoji = {'High': '🔴', 'Mid': '🟡', 'Low': '🟢'}.get(lead.priority, '⚪')
            
            response = (
                f"✅ **Lead stored in CRM successfully!**\n\n"
                f"📋 **Subject:** {lead.lead_subject}\n"
                f"{priority_emoji} **Priority:** {lead.priority}\n"
                f"👤 **Owner:** {lead.owner}\n"
                f"📊 **Status:** {lead.status}\n"
                f"🆔 **Lead ID:** {lead.id}"
            )
            
            return {
                "is_mail_me": False,
                "agent_response": response,
                "action_type": "crm_store",
                "success": True,
                "lead_id": lead.id
            }
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"[agents.py] Error storing CRM lead: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error storing lead in CRM: {str(e)}",
            "action_type": "crm_store",
            "success": False,
            "error": str(e)
        }


async def handle_crm_read(message: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle CRM read command - retrieve and display leads for the user's tenant.
    
    Args:
        message: The user's message
        user_data: User information from database
        
    Returns:
        dict: Processing result
    """
    from pareto_agents.database import get_db_manager
    from pareto_agents.crm_service import CRMService
    
    try:
        tenant_id = user_data.get('tenant_id')
        
        if not tenant_id:
            return {
                "is_mail_me": False,
                "agent_response": "❌ Unable to identify your tenant. Please contact support.",
                "action_type": "crm_read",
                "success": False
            }
        
        # Parse any filters from the message
        message_lower = message.lower()
        status_filter = None
        priority_filter = None
        
        # Check for status filters
        if 'open' in message_lower:
            status_filter = 'Open'
        elif 'in progress' in message_lower or 'progress' in message_lower:
            status_filter = 'In Progress'
        elif 'closed' in message_lower:
            status_filter = 'Closed'
        elif 'rejected' in message_lower:
            status_filter = 'Rejected'
        
        # Check for priority filters
        if 'high' in message_lower or 'urgent' in message_lower:
            priority_filter = 'High'
        elif 'mid' in message_lower or 'medium' in message_lower:
            priority_filter = 'Mid'
        elif 'low' in message_lower:
            priority_filter = 'Low'
        
        logger.info(f"[agents.py] CRM read for tenant {tenant_id}, status_filter={status_filter}, priority_filter={priority_filter}")
        
        # Get leads from CRM
        db_manager = get_db_manager()
        db_session = db_manager.get_session()
        
        try:
            crm_service = CRMService(db_session)
            leads = crm_service.get_leads_by_tenant(
                tenant_id=tenant_id,
                status=status_filter,
                priority=priority_filter,
                limit=10  # Limit to 10 most recent leads for chat
            )
            
            # Get stats
            stats = crm_service.get_lead_stats(tenant_id=tenant_id)
            
            # Format response
            if not leads:
                filter_info = ""
                if status_filter:
                    filter_info += f" with status '{status_filter}'"
                if priority_filter:
                    filter_info += f" with priority '{priority_filter}'"
                
                response = f"📋 No leads found{filter_info} in your CRM."
            else:
                response = format_leads_for_response(leads, include_details=True)
                
                # Add stats summary
                response += f"\n\n📊 **Summary:** {stats['total']} total leads"
                response += f" | Open: {stats['by_status'].get('Open', 0)}"
                response += f" | In Progress: {stats['by_status'].get('In Progress', 0)}"
                response += f" | High Priority: {stats['by_priority'].get('High', 0)}"
            
            return {
                "is_mail_me": False,
                "agent_response": response,
                "action_type": "crm_read",
                "success": True,
                "lead_count": len(leads)
            }
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"[agents.py] Error reading CRM leads: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error reading from CRM: {str(e)}",
            "action_type": "crm_read",
            "success": False,
            "error": str(e)
        }


async def handle_help_command(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle help command - return the help/knowledgebase content.
    
    Args:
        user_data: User information from database
        
    Returns:
        dict: Processing result with help content
    """
    import os
    
    try:
        # Get the path to help.txt
        # First try relative to the pareto_agents directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        help_file_paths = [
            os.path.join(base_dir, 'knowledgebases', 'help.txt'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledgebases', 'help.txt'),
            '/app/knowledgebases/help.txt',  # Heroku path
            'knowledgebases/help.txt',  # Relative path
        ]
        
        help_content = None
        for help_path in help_file_paths:
            if os.path.exists(help_path):
                with open(help_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
                logger.info(f"[agents.py] Loaded help from: {help_path}")
                break
        
        if not help_content:
            logger.warning("[agents.py] Help file not found in any expected location")
            help_content = """**Pareto Help**

Sorry, the help file could not be loaded. Please contact support.

Basic commands:
- "Add in CRM ..." - Store information in CRM
- "Get CRM ..." - Retrieve CRM leads
- "Mail me ..." - Send yourself an email
- "Book a meeting ..." - Schedule calendar events
"""
        
        # Get user's first name for personalized greeting
        user_name = user_data.get('first_name', 'there') if user_data else 'there'
        
        # Format the response
        response = f"Hi {user_name}! Here's the Pareto help guide:\n\n{help_content}"
        
        logger.info(f"[agents.py] Help command processed for user {user_name}")
        
        return {
            "is_mail_me": False,
            "agent_response": response,
            "action_type": "help",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"[agents.py] Error loading help: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error loading help: {str(e)}",
            "action_type": "help",
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Process Message Function
# ============================================================================

async def process_message(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process incoming message through agents
    Routes to appropriate agent based on message classification

    Args:
        message (str): User's message
        phone_number (str): User's phone number (session ID)
        user_data (dict): User information from database

    Returns:
        dict: Processing result with agent response and action type
    """
    try:
        logger.info(f"[agents.py] Processing message from {phone_number}: '{message[:50]}...'")

        # Get current date/time context
        datetime_context = get_current_datetime_context()
        logger.info(f"[agents.py] DateTime context: {datetime_context}")

        # Classify the message
        message_type = classify_message(message)
        logger.info(f"[agents.py] Message classified as: {message_type}")
        
        # Get memory context for personalization
        memory_context = get_memory_context(message, phone_number)
        if memory_context:
            logger.info(f"[agents.py] Retrieved memory context for user")
        
        # Prepend datetime context and memory to message for agent processing
        if memory_context:
            message_with_context = f"[SYSTEM: {datetime_context}]\n\n[MEMORY: {memory_context}]\n\nUser message: {message}"
        else:
            message_with_context = f"[SYSTEM: {datetime_context}]\n\nUser message: {message}"

        # 0. Handle HELP command
        if message_type == 'help':
            logger.info("[agents.py] Routing to Help handler.")
            return await handle_help_command(user_data)

        # 1. Handle 'mail me' command
        if message_type == 'mail_me':
            logger.info("[agents.py] Routing to MailMeHandler.")
            mail_content = MailMeHandler.extract_mail_me_content(message)
            user_name = f"{user_data.get('first_name')} {user_data.get('last_name')}"
            user_email = user_data.get('email')

            mail_me_request = MailMeHandler.create_mail_me_request(
                content=mail_content, user_email=user_email, user_name=user_name
            )

            response = MailMeHandler.format_mail_me_response(
                user_name=user_name, subject=mail_me_request.subject, recipient=user_email
            )

            return {
                "is_mail_me": True,
                "agent_response": response,
                "action_type": "mail_me",
                "mail_me_request": mail_me_request,
            }

        # 2. Handle CRM store command
        if message_type == 'crm_store':
            logger.info("[agents.py] Routing to CRM Store handler.")
            return await handle_crm_store(message, user_data)

        # 3. Handle CRM read command
        if message_type == 'crm_read':
            logger.info("[agents.py] Routing to CRM Read handler.")
            return await handle_crm_read(message, user_data)

        # 4. Handle calendar actions (book, create, update, delete)
        if message_type == 'calendar_action':
            logger.info("[agents.py] Routing to Calendar Manager for action.")
            runner = Runner()
            result = await runner.run(
                starting_agent=calendar_agent,
                input=message_with_context,
            )

            agent_response = _extract_response(result)
            logger.info(f"[agents.py] Calendar Manager response: '{agent_response[:100]}...'")

            # Store calendar action in memory
            try:
                add_conversation_memory(
                    user_message=message,
                    assistant_response=agent_response,
                    phone_number=phone_number,
                    metadata={"action_type": "calendar"}
                )
            except Exception as mem_error:
                logger.warning(f"[agents.py] Failed to store memory: {mem_error}")

            return {
                "is_mail_me": False,
                "agent_response": agent_response,
                "action_type": "calendar",
                "raw_result": result,
            }

        # 5. Handle email actions (send, compose)
        if message_type == 'email_action':
            logger.info("[agents.py] Routing to Email Manager for action.")
            runner = Runner()
            result = await runner.run(
                starting_agent=email_agent,
                input=message_with_context,
            )

            agent_response = _extract_response(result)
            logger.info(f"[agents.py] Email Manager response: '{agent_response[:100]}...'")

            # Store email action in memory
            try:
                add_conversation_memory(
                    user_message=message,
                    assistant_response=agent_response,
                    phone_number=phone_number,
                    metadata={"action_type": "email"}
                )
            except Exception as mem_error:
                logger.warning(f"[agents.py] Failed to store memory: {mem_error}")

            return {
                "is_mail_me": False,
                "agent_response": agent_response,
                "action_type": "email",
                "raw_result": result,
            }

        # 6. Handle queries, summaries, and general conversation via Personal Assistant
        logger.info("[agents.py] Routing to Personal Assistant.")
        runner = Runner()
        result = await runner.run(
            starting_agent=personal_assistant_agent,
            input=message_with_context,
        )

        agent_response = _extract_response(result)
        logger.info(f"[agents.py] Personal Assistant response: '{agent_response[:100]}...'")

        # Store conversation in memory for future context
        try:
            add_conversation_memory(
                user_message=message,
                assistant_response=agent_response,
                phone_number=phone_number,
                metadata={"action_type": "personal_assistant"}
            )
        except Exception as mem_error:
            logger.warning(f"[agents.py] Failed to store memory: {mem_error}")

        return {
            "is_mail_me": False,
            "agent_response": agent_response,
            "action_type": "personal_assistant",
            "raw_result": result,
        }

    except Exception as e:
        logger.error(f"[agents.py] Error processing message: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error processing message: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }


def _extract_response(result) -> str:
    """
    Extract the text response from an agent result
    """
    if hasattr(result, 'final_output') and result.final_output:
        return str(result.final_output)
    if hasattr(result, 'raw_responses') and result.raw_responses:
        last_response = result.raw_responses[-1] if isinstance(result.raw_responses, list) else result.raw_responses
        return str(last_response)
    return str(result)


# ============================================================================
# Synchronous Wrapper for Flask
# ============================================================================

def process_message_sync(
    message: str,
    phone_number: str,
    user_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for process_message for Flask compatibility.
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async function
        result = loop.run_until_complete(
            process_message(message, phone_number, user_data)
        )

        return result

    except Exception as e:
        logger.error(f"[agents.py] Error in sync wrapper: {str(e)}", exc_info=True)
        return {
            "is_mail_me": False,
            "agent_response": f"❌ Error: {str(e)}",
            "action_type": "error",
            "error": str(e),
        }
