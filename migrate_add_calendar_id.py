"""
Database Migration Script: Add google_calendar_id column to users table

This script adds the google_calendar_id column to the existing users table.
Run this script once after deploying the updated code.

Usage:
    python migrate_add_calendar_id.py

Or run via Heroku:
    heroku run python migrate_add_calendar_id.py
"""

import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
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
        # Local development fallback
        return 'sqlite:///configurations/pareto.db'


def run_migration():
    """Run the migration to add google_calendar_id column"""
    database_url = get_database_url()
    logger.info(f"Connecting to database...")
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check if column already exists
        if 'postgresql' in database_url:
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'google_calendar_id'
            """)
        else:
            # SQLite
            check_sql = text("PRAGMA table_info(users)")
        
        result = conn.execute(check_sql)
        
        if 'postgresql' in database_url:
            column_exists = result.fetchone() is not None
        else:
            # SQLite - check if column exists in table info
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'google_calendar_id' in columns
        
        if column_exists:
            logger.info("✅ Column 'google_calendar_id' already exists. No migration needed.")
            return
        
        # Add the column
        logger.info("Adding 'google_calendar_id' column to users table...")
        
        if 'postgresql' in database_url:
            alter_sql = text("""
                ALTER TABLE users 
                ADD COLUMN google_calendar_id VARCHAR(255) NULL
            """)
        else:
            # SQLite
            alter_sql = text("""
                ALTER TABLE users 
                ADD COLUMN google_calendar_id TEXT NULL
            """)
        
        conn.execute(alter_sql)
        conn.commit()
        
        logger.info("✅ Migration completed successfully! Column 'google_calendar_id' added to users table.")


if __name__ == '__main__':
    run_migration()
