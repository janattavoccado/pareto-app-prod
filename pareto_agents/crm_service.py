"""
CRM Service

Provides business logic for CRM operations:
- Lead creation with LLM-powered field extraction
- Lead CRUD operations
- Tenant-isolated data access

File location: pareto_agents/crm_service.py
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from openai import OpenAI
from sqlalchemy.orm import Session

from pareto_agents.crm_models import (
    CRMLead, LeadExtraction, LeadPriority, LeadStatus,
    LeadContentStructure, LeadAction
)
from pareto_agents.database import Tenant, User

logger = logging.getLogger(__name__)


class CRMService:
    """Service class for CRM operations"""
    
    def __init__(self, db_session: Session):
        """
        Initialize CRM service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.client = OpenAI()  # Uses OPENAI_API_KEY env var
    
    def extract_lead_info(self, message: str, user_name: str) -> LeadExtraction:
        """
        Use LLM to extract structured lead information from a message
        
        Args:
            message: The raw message to process
            user_name: Name of the user creating the lead (for default owner)
            
        Returns:
            LeadExtraction: Structured lead information
        """
        try:
            # Create the extraction prompt
            system_prompt = """You are a CRM assistant that extracts structured information from messages to create leads.

Analyze the message and extract:
1. **Subject**: A concise subject line (max 100 chars) summarizing the lead
2. **Content**: Structured information including summary, key points, contact info, company, product interest, budget, timeline
3. **Priority**: Determine priority based on:
   - HIGH: Urgent requests, high-value opportunities, time-sensitive matters, VIP clients
   - MID: Standard inquiries, moderate value, normal timeline
   - LOW: Informational requests, low urgency, early-stage inquiries
4. **Actions**: Extract any action items mentioned (calls, meetings, follow-ups, etc.)
5. **Owner**: If someone is mentioned to handle this (e.g., "assign to John", "for Sarah"), extract their name

Return the information in the specified JSON format."""

            user_prompt = f"""Extract lead information from this message:

"{message}"

Default owner (if no one else is mentioned): {user_name}"""

            response = self.client.beta.chat.completions.parse(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=LeadExtraction
            )
            
            extraction = response.choices[0].message.parsed
            
            # Set default owner if not extracted
            if not extraction.owner:
                extraction.owner = user_name
            
            logger.info(f"Extracted lead info: subject='{extraction.subject}', priority={extraction.priority}")
            return extraction
            
        except Exception as e:
            logger.error(f"Error extracting lead info: {e}")
            # Return basic extraction on error
            return LeadExtraction(
                subject=message[:100] if len(message) > 100 else message,
                content=LeadContentStructure(
                    summary=message,
                    key_points=[]
                ),
                priority=LeadPriority.MID,
                actions=[],
                owner=user_name
            )
    
    def create_lead(
        self,
        message: str,
        tenant_id: int,
        user_id: int
    ) -> CRMLead:
        """
        Create a new CRM lead with LLM-powered extraction
        
        Args:
            message: The raw message to create lead from
            tenant_id: ID of the tenant
            user_id: ID of the user creating the lead
            
        Returns:
            CRMLead: The created lead
        """
        # Get tenant and user info
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not tenant or not user:
            raise ValueError("Invalid tenant_id or user_id")
        
        # Extract lead information using LLM
        extraction = self.extract_lead_info(message, user.full_name)
        
        # Create the lead
        lead = CRMLead(
            tenant_id=tenant_id,
            tenant_name=tenant.company_name,
            user_id=user_id,
            user_name=user.full_name,
            lead_subject=extraction.subject,
            lead_content=extraction.content.model_dump_json(),
            priority=extraction.priority.value,
            actions=json.dumps([a.model_dump() for a in extraction.actions]) if extraction.actions else None,
            owner=extraction.owner or user.full_name,
            status=LeadStatus.OPEN.value,
            original_message=message
        )
        
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        
        logger.info(f"Created CRM lead: id={lead.id}, subject='{lead.lead_subject}'")
        return lead
    
    def get_leads_by_tenant(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CRMLead]:
        """
        Get leads for a specific tenant
        
        Args:
            tenant_id: ID of the tenant
            status: Optional status filter
            priority: Optional priority filter
            limit: Maximum number of leads to return
            offset: Number of leads to skip
            
        Returns:
            List[CRMLead]: List of leads
        """
        query = self.db.query(CRMLead).filter(CRMLead.tenant_id == tenant_id)
        
        if status:
            query = query.filter(CRMLead.status == status)
        if priority:
            query = query.filter(CRMLead.priority == priority)
        
        query = query.order_by(CRMLead.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_all_leads(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tenant_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CRMLead]:
        """
        Get all leads (admin access)
        
        Args:
            status: Optional status filter
            priority: Optional priority filter
            tenant_id: Optional tenant filter
            limit: Maximum number of leads to return
            offset: Number of leads to skip
            
        Returns:
            List[CRMLead]: List of leads
        """
        query = self.db.query(CRMLead)
        
        if tenant_id:
            query = query.filter(CRMLead.tenant_id == tenant_id)
        if status:
            query = query.filter(CRMLead.status == status)
        if priority:
            query = query.filter(CRMLead.priority == priority)
        
        query = query.order_by(CRMLead.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_lead_by_id(self, lead_id: int, tenant_id: Optional[int] = None) -> Optional[CRMLead]:
        """
        Get a specific lead by ID
        
        Args:
            lead_id: ID of the lead
            tenant_id: Optional tenant ID for access control
            
        Returns:
            CRMLead or None
        """
        query = self.db.query(CRMLead).filter(CRMLead.id == lead_id)
        
        if tenant_id:
            query = query.filter(CRMLead.tenant_id == tenant_id)
        
        return query.first()
    
    def update_lead(
        self,
        lead_id: int,
        tenant_id: Optional[int] = None,
        **updates
    ) -> Optional[CRMLead]:
        """
        Update a lead
        
        Args:
            lead_id: ID of the lead
            tenant_id: Optional tenant ID for access control
            **updates: Fields to update
            
        Returns:
            CRMLead or None
        """
        lead = self.get_lead_by_id(lead_id, tenant_id)
        
        if not lead:
            return None
        
        # Update allowed fields
        allowed_fields = ['lead_subject', 'priority', 'owner', 'status']
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(lead, field, value)
        
        lead.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(lead)
        
        logger.info(f"Updated CRM lead: id={lead_id}, updates={list(updates.keys())}")
        return lead
    
    def delete_lead(self, lead_id: int, tenant_id: Optional[int] = None) -> bool:
        """
        Delete a lead
        
        Args:
            lead_id: ID of the lead
            tenant_id: Optional tenant ID for access control
            
        Returns:
            bool: True if deleted, False if not found
        """
        lead = self.get_lead_by_id(lead_id, tenant_id)
        
        if not lead:
            return False
        
        self.db.delete(lead)
        self.db.commit()
        
        logger.info(f"Deleted CRM lead: id={lead_id}")
        return True
    
    def get_lead_stats(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get lead statistics
        
        Args:
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Dict with statistics
        """
        from sqlalchemy import func
        
        query = self.db.query(CRMLead)
        if tenant_id:
            query = query.filter(CRMLead.tenant_id == tenant_id)
        
        total = query.count()
        
        # Count by status
        status_counts = {}
        for status in LeadStatus:
            count = query.filter(CRMLead.status == status.value).count()
            status_counts[status.value] = count
        
        # Count by priority
        priority_counts = {}
        for priority in LeadPriority:
            count = query.filter(CRMLead.priority == priority.value).count()
            priority_counts[priority.value] = count
        
        return {
            'total': total,
            'by_status': status_counts,
            'by_priority': priority_counts
        }
