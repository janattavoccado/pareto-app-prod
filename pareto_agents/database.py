"""
Database Models and Configuration

Provides SQLAlchemy ORM models for:
- Administrators
- Tenants
- Users
- Admin Sessions
- Audit Logs

File location: pareto_agents/database.py
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class Administrator(Base):
    """Administrator account model"""
    __tablename__ = 'administrators'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    sessions = relationship('AdminSession', back_populates='administrator', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='administrator', cascade='all, delete-orphan')
    tenants = relationship('Tenant', back_populates='created_by_admin', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Administrator(id={self.id}, username={self.username}, email={self.email})>"


class Tenant(Base):
    """Tenant (Company) model"""
    __tablename__ = 'tenants'
    
    id = Column(Integer, primary_key=True)
    # 'name' column for backwards compatibility with existing database schema
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    company_slug = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_admin_id = Column(Integer, ForeignKey('administrators.id'), nullable=False)
    
    # Relationships
    created_by_admin = relationship('Administrator', back_populates='tenants')
    users = relationship('User', back_populates='tenant', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_tenants_slug', 'company_slug'),
    )
    
    def to_dict(self, include_users=False):
        data = {
            'id': self.id,
            'company_name': self.company_name,
            'company_slug': self.company_slug,
            'email': self.email,
            'phone': self.phone,
            'active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_count': len(self.users)
        }
        if include_users:
            data['users'] = [user.to_dict() for user in self.users]
        return data

    def __repr__(self):
        return f"<Tenant(id={self.id}, company_name={self.company_name}, slug={self.company_slug})>"


class User(Base):
    """User (Team member) model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    phone_number = Column(String(20), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255))
    is_enabled = Column(Boolean, default=True)
    # Google token stored as Base64 encrypted string (replaces file-based tokens)
    google_token_base64 = Column(Text, nullable=True)
    google_token_updated_at = Column(DateTime, nullable=True)
    # Google Calendar ID for user's personal calendar (within shared Google account)
    google_calendar_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship('Tenant', back_populates='users')
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'phone_number', name='uq_tenant_phone'),
        Index('idx_users_tenant_id', 'tenant_id'),
        Index('idx_users_phone', 'phone_number'),
        Index('idx_users_tenant_phone', 'tenant_id', 'phone_number'),
    )
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_google_token(self) -> bool:
        """Check if user has a Google token configured"""
        return bool(self.google_token_base64)
    
    def has_google_calendar(self) -> bool:
        """Check if user has a Google Calendar configured"""
        return bool(self.google_calendar_id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'phone_number': self.phone_number,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'is_enabled': self.is_enabled,
            'has_google_token': self.has_google_token(),
            'google_token_updated_at': self.google_token_updated_at.isoformat() if self.google_token_updated_at else None,
            'google_calendar_id': self.google_calendar_id,
            'has_google_calendar': self.has_google_calendar(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone_number}, name={self.full_name})>"


class AdminSession(Base):
    """Administrator session model"""
    __tablename__ = 'admin_sessions'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('administrators.id'), nullable=False)
    session_token = Column(String(500), unique=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    administrator = relationship('Administrator', back_populates='sessions')
    
    __table_args__ = (
        Index('idx_admin_sessions_admin_id', 'admin_id'),
        Index('idx_admin_sessions_token', 'session_token'),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<AdminSession(id={self.id}, admin_id={self.admin_id}, expired={self.is_expired})>"


class AuditLog(Base):
    """Audit log model for tracking administrative actions"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('administrators.id'))
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    changes = Column(Text)  # JSON string of changes
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    administrator = relationship('Administrator', back_populates='audit_logs')
    
    __table_args__ = (
        Index('idx_audit_logs_admin_id', 'admin_id'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, entity={self.entity_type}:{self.entity_id})>"


# ============================================================================
# Database Connection and Session Management
# ============================================================================

class DatabaseManager:
    """Manages database connection and session lifecycle"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            database_url: SQLAlchemy database URL. If None, checks for DATABASE_URL env var,
                         then falls back to SQLite.
        """
        if database_url is None:
            # Check for Heroku DATABASE_URL environment variable
            database_url = os.environ.get('DATABASE_URL')
            
            if database_url:
                # Heroku uses 'postgres://' but SQLAlchemy requires 'postgresql://'
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace('postgres://', 'postgresql://', 1)
                logger.info("Using PostgreSQL database from DATABASE_URL environment variable")
            else:
                # Default to SQLite in configurations directory (for local development)
                db_dir = Path('configurations')
                db_dir.mkdir(exist_ok=True)
                database_url = f'sqlite:///{db_dir}/pareto.db'
                logger.info("Using SQLite database for local development")
        
        self.database_url = database_url
        
        # Log database type (hide credentials)
        if 'postgresql' in database_url:
            logger.info("Initializing PostgreSQL database connection")
        elif 'sqlite' in database_url:
            logger.info(f"Initializing database: {database_url}")
        else:
            logger.info("Initializing database connection")
        
        # Create engine
        if database_url.startswith('sqlite://'):
            # SQLite specific configuration
            self.engine = create_engine(
                database_url,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool
            )
        else:
            # For PostgreSQL and other databases
            # Use connection pooling for production
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True  # Verify connections before use
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create all tables in the database (if they don't exist)"""
        try:
            # Use checkfirst=True to avoid errors when tables already exist
            # This is important for PostgreSQL which doesn't handle duplicate CREATE TABLE gracefully
            Base.metadata.create_all(self.engine, checkfirst=True)
            logger.info("✅ Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"❌ Error creating database tables: {e}")
            # Don't raise on duplicate table errors - they're expected in multi-worker environments
            if 'already exists' in str(e).lower() or 'duplicate key' in str(e).lower():
                logger.warning("Tables already exist, continuing...")
            else:
                raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()
        logger.info("Database connection closed")


# ============================================================================
# Global Database Manager Instance
# ============================================================================

_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Get or create the global database manager instance
    
    Args:
        database_url: SQLAlchemy database URL (used only on first call)
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_db_session() -> Session:
    """
    Get a new database session
    
    Usage in Flask:
        @app.route('/example')
        def example():
            db = get_db_session()
            try:
                # Use db session
                pass
            finally:
                db.close()
    
    Returns:
        SQLAlchemy Session
    """
    return get_db_manager().get_session()


# ============================================================================
# Database Utilities
# ============================================================================

def reset_database(database_url: Optional[str] = None):
    """
    Reset database - drops all tables and recreates them
    WARNING: This will delete all data!
    
    Args:
        database_url: SQLAlchemy database URL
    """
    manager = DatabaseManager(database_url)
    logger.warning("⚠️  RESETTING DATABASE - ALL DATA WILL BE DELETED!")
    Base.metadata.drop_all(manager.engine)
    manager._create_tables()
    logger.warning("✅ Database reset complete")


if __name__ == '__main__':
    # Test database initialization
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = get_db_manager()
    logger.info("Database initialized successfully")
    
    # Test session
    session = get_db_session()
    logger.info(f"Test session created: {session}")
    session.close()

def init_db(database_url: Optional[str] = None):
    """
    Initialize the database and create tables.
    
    Args:
        database_url: SQLAlchemy database URL.
    """
    get_db_manager(database_url)
