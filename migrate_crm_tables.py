#!/usr/bin/env python3
"""
CRM Tables Migration Script

Creates the CRM-related tables:
- crm_leads: Stores leads for all tenants
- user_credentials: User login credentials for CRM portal
- user_sessions: User session management

Run this script after deploying the new code:
    heroku run python migrate_crm_tables.py

File location: migrate_crm_tables.py
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Heroku uses 'postgres://' but SQLAlchemy requires 'postgresql://'
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        # Local development - use SQLite
        return 'sqlite:///configurations/pareto.db'


def run_migration():
    """Run the CRM tables migration"""
    from sqlalchemy import create_engine, text, inspect
    
    database_url = get_database_url()
    is_postgres = 'postgresql' in database_url
    
    logger.info(f"Connecting to {'PostgreSQL' if is_postgres else 'SQLite'} database...")
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    print("=" * 60)
    print("CRM Tables Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check existing tables
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        
        # ================================================================
        # Create crm_leads table
        # ================================================================
        if 'crm_leads' not in existing_tables:
            logger.info("Creating 'crm_leads' table...")
            
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE crm_leads (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        tenant_name VARCHAR(255) NOT NULL,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        user_name VARCHAR(255) NOT NULL,
                        lead_subject VARCHAR(255) NOT NULL,
                        lead_content TEXT NOT NULL,
                        priority VARCHAR(20) DEFAULT 'Mid',
                        actions TEXT,
                        owner VARCHAR(255) NOT NULL,
                        status VARCHAR(20) DEFAULT 'Open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        original_message TEXT
                    )
                """))
                
                # Create indexes
                conn.execute(text("CREATE INDEX idx_crm_leads_tenant_id ON crm_leads(tenant_id)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_user_id ON crm_leads(user_id)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_status ON crm_leads(status)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_priority ON crm_leads(priority)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_created_at ON crm_leads(created_at)"))
            else:
                # SQLite
                conn.execute(text("""
                    CREATE TABLE crm_leads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        tenant_name VARCHAR(255) NOT NULL,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        user_name VARCHAR(255) NOT NULL,
                        lead_subject VARCHAR(255) NOT NULL,
                        lead_content TEXT NOT NULL,
                        priority VARCHAR(20) DEFAULT 'Mid',
                        actions TEXT,
                        owner VARCHAR(255) NOT NULL,
                        status VARCHAR(20) DEFAULT 'Open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        original_message TEXT
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_crm_leads_tenant_id ON crm_leads(tenant_id)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_user_id ON crm_leads(user_id)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_status ON crm_leads(status)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_priority ON crm_leads(priority)"))
                conn.execute(text("CREATE INDEX idx_crm_leads_created_at ON crm_leads(created_at)"))
            
            conn.commit()
            print("✅ Created 'crm_leads' table with indexes")
        else:
            print("✓ 'crm_leads' table already exists")
        
        # ================================================================
        # Create user_credentials table
        # ================================================================
        if 'user_credentials' not in existing_tables:
            logger.info("Creating 'user_credentials' table...")
            
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE user_credentials (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                        password_hash VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reset_token VARCHAR(255),
                        reset_token_expires TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id)"))
            else:
                conn.execute(text("""
                    CREATE TABLE user_credentials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                        password_hash VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reset_token VARCHAR(255),
                        reset_token_expires TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id)"))
            
            conn.commit()
            print("✅ Created 'user_credentials' table")
        else:
            print("✓ 'user_credentials' table already exists")
        
        # ================================================================
        # Create user_sessions table
        # ================================================================
        if 'user_sessions' not in existing_tables:
            logger.info("Creating 'user_sessions' table...")
            
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE user_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        session_token VARCHAR(500) UNIQUE NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id)"))
                conn.execute(text("CREATE INDEX idx_user_sessions_token ON user_sessions(session_token)"))
            else:
                conn.execute(text("""
                    CREATE TABLE user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        session_token VARCHAR(500) UNIQUE NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id)"))
                conn.execute(text("CREATE INDEX idx_user_sessions_token ON user_sessions(session_token)"))
            
            conn.commit()
            print("✅ Created 'user_sessions' table")
        else:
            print("✓ 'user_sessions' table already exists")
    
    print()
    print("=" * 60)
    print("✅ CRM Migration completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. The CRM tables are now ready for use")
    print("2. Users can set passwords via the user portal")
    print("3. Admins can view all tenant CRM data from the dashboard")


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
