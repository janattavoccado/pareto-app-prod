"""
CRM Database Models and Pydantic Schemas

Provides:
- SQLAlchemy ORM model for CRM Leads (tenant-isolated)
- Pydantic models for LLM-powered field extraction
- User authentication model for CRM access

File location: pareto_agents/crm_models.py
"""

import os
import logging
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

# Import Base from database.py
from pareto_agents.database import Base

logger = logging.getLogger(__name__)


# ============================================================================
# Enums for CRM Fields
# ============================================================================

class LeadPriority(str, Enum):
    """Priority levels for leads"""
    LOW = "Low"
    MID = "Mid"
    HIGH = "High"


class LeadStatus(str, Enum):
    """Status options for leads"""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"
    REJECTED = "Rejected"


# ============================================================================
# Pydantic Models for LLM Field Extraction
# ============================================================================

class LeadAction(BaseModel):
    """Structured action item extracted from lead message"""
    action_type: str = Field(..., description="Type of action (e.g., 'call', 'email', 'meeting', 'follow-up')")
    description: str = Field(..., description="Description of the action to take")
    due_date: Optional[str] = Field(None, description="Due date if mentioned (ISO format)")
    assignee: Optional[str] = Field(None, description="Person assigned to this action if mentioned")


class LeadContentStructure(BaseModel):
    """Structured content extracted from lead message"""
    summary: str = Field(..., description="Brief summary of the lead content")
    key_points: List[str] = Field(default_factory=list, description="Key points from the message")
    contact_info: Optional[str] = Field(None, description="Contact information if mentioned")
    company_mentioned: Optional[str] = Field(None, description="Company name if mentioned")
    product_interest: Optional[str] = Field(None, description="Product or service of interest")
    budget: Optional[str] = Field(None, description="Budget information if mentioned")
    timeline: Optional[str] = Field(None, description="Timeline or urgency information")
    notes: Optional[str] = Field(None, description="Additional notes or context")


class LeadExtraction(BaseModel):
    """
    Complete lead extraction model for LLM processing
    
    The LLM will analyze the user message and extract structured information
    """
    subject: str = Field(..., description="A concise subject line for the lead (max 100 chars)")
    content: LeadContentStructure = Field(..., description="Structured content information")
    priority: LeadPriority = Field(
        default=LeadPriority.MID,
        description="Priority level based on urgency, value, and context. HIGH for urgent/high-value, LOW for informational"
    )
    actions: List[LeadAction] = Field(
        default_factory=list,
        description="List of action items extracted from the message"
    )
    owner: Optional[str] = Field(
        None,
        description="Owner name if mentioned in the message (e.g., 'assign to John')"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject": "New partnership inquiry from TechCorp",
                "content": {
                    "summary": "TechCorp is interested in partnership for AI solutions",
                    "key_points": [
                        "Looking for AI integration",
                        "Budget of $50,000",
                        "Q2 timeline"
                    ],
                    "contact_info": "john@techcorp.com",
                    "company_mentioned": "TechCorp",
                    "product_interest": "AI Solutions",
                    "budget": "$50,000",
                    "timeline": "Q2 2026"
                },
                "priority": "High",
                "actions": [
                    {
                        "action_type": "call",
                        "description": "Schedule discovery call with TechCorp",
                        "due_date": "2026-01-10",
                        "assignee": "Sales Team"
                    }
                ],
                "owner": "John"
            }
        }


# ============================================================================
# SQLAlchemy Models
# ============================================================================

class CRMLead(Base):
    """CRM Lead model - stores leads for each tenant"""
    __tablename__ = 'crm_leads'
    
    id = Column(Integer, primary_key=True)
    
    # Tenant and User references
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    tenant_name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user_name = Column(String(255), nullable=False)  # Creator of the lead
    
    # Lead information (LLM-extracted)
    lead_subject = Column(String(255), nullable=False)
    lead_content = Column(Text, nullable=False)  # JSON string of LeadContentStructure
    priority = Column(String(20), default='Mid')  # Low, Mid, High
    actions = Column(Text, nullable=True)  # JSON string of List[LeadAction]
    
    # Ownership and status
    owner = Column(String(255), nullable=False)  # Default to user_name if not specified
    status = Column(String(20), default='Open')  # Open, In Progress, Closed, Rejected
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Original message for reference
    original_message = Column(Text, nullable=True)
    
    # Relationships
    tenant = relationship('Tenant', backref='crm_leads')
    user = relationship('User', backref='crm_leads')
    
    __table_args__ = (
        Index('idx_crm_leads_tenant_id', 'tenant_id'),
        Index('idx_crm_leads_user_id', 'user_id'),
        Index('idx_crm_leads_status', 'status'),
        Index('idx_crm_leads_priority', 'priority'),
        Index('idx_crm_leads_created_at', 'created_at'),
    )
    
    def to_dict(self):
        """Convert lead to dictionary"""
        import json
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'tenant_name': self.tenant_name,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'lead_subject': self.lead_subject,
            'lead_content': json.loads(self.lead_content) if self.lead_content else {},
            'priority': self.priority,
            'actions': json.loads(self.actions) if self.actions else [],
            'owner': self.owner,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'original_message': self.original_message
        }
    
    def __repr__(self):
        return f"<CRMLead(id={self.id}, subject={self.lead_subject[:30]}..., status={self.status})>"


class UserCredential(Base):
    """User credentials for CRM portal login"""
    __tablename__ = 'user_credentials'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('User', backref='credentials')
    
    __table_args__ = (
        Index('idx_user_credentials_user_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<UserCredential(id={self.id}, user_id={self.user_id})>"


class UserSession(Base):
    """User session model for CRM portal"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(500), unique=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    user = relationship('User', backref='sessions')
    
    __table_args__ = (
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_token', 'session_token'),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expired={self.is_expired})>"
