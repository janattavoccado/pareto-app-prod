import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# --- Database Configuration ---
# Heroku sets DATABASE_URL for PostgreSQL. If not set, use local SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pareto.db")

# SQLAlchemy setup
Base = declarative_base()

class Tenant(Base):
    """Database model for application tenants (organizations)."""
    __tablename__ = 'tenants'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Tenant(name='{self.name}')>"

class User(Base):
    """Database model for user information and Google tokens."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=True) # Added foreign key
    phone_number = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    is_enabled = Column(Boolean, default=False)
    google_token_base64 = Column(String) # Stores the base64 encoded Google token
    
    def __repr__(self):
        return f"<User(phone_number='{self.phone_number}', email='{self.email}')>"

class Administrator(Base):
    """Database model for application administrators."""
    __tablename__ = 'administrators'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Administrator(username='{self.username}')>"

class AdminSession(Base):
    """Database model for administrator sessions."""
    __tablename__ = 'admin_sessions'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('administrators.id'), nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String) # Added missing column
    user_agent = Column(String) # Added missing column
    is_active = Column(Boolean, default=True) # Added missing column from log error
    
    def __repr__(self):
        return f"<AdminSession(admin_id='{self.admin_id}', token='{self.session_token[:10]}...')>"

class AuditLog(Base):
    """Database model for audit logging of administrative actions."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    admin_id = Column(Integer, ForeignKey('administrators.id'), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    ip_address = Column(String) # Added missing column
    user_agent = Column(String) # Added missing column
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', timestamp='{self.timestamp}')>"

# Configure engine for Heroku PostgreSQL or local SQLite
if DATABASE_URL.startswith("postgres://"):
    # Fix for Heroku's old postgres URL scheme
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Heroku requires SSL mode for external connections, but we'll rely on Heroku's default config
    engine = create_engine(DATABASE_URL)
else:
    # SQLite - check_same_thread is required for Flask development
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Returns a direct database session."""
    return SessionLocal()

# Compatibility function for app.py
def get_db_manager():
    """
    Compatibility function for app.py. Returns a new database session.
    The caller is responsible for closing the session.
    """
    return SessionLocal()

# Initialize the database when this module is imported
init_db()
