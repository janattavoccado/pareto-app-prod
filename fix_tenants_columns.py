"""
Fix missing columns in tenants table

This script adds the missing created_at and updated_at columns to the tenants table in PostgreSQL.
Run this script after deploying to Heroku to ensure the database schema matches the SQLAlchemy models.

Usage:
    heroku run python fix_tenants_columns.py --app pareto-app-prod
"""

import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pareto.db")

def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def fix_tenants_table():
    """Add missing columns to tenants table"""
    
    try:
        # Fix Heroku's old postgres URL scheme
        if DATABASE_URL.startswith("postgres://"):
            db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        else:
            db_url = DATABASE_URL
        
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            # Check if we're using PostgreSQL
            if 'postgresql' in db_url or 'postgres' in db_url:
                logger.info("🔧 Fixing PostgreSQL tenants table...")
                
                # Check if created_at column exists
                if not column_exists(connection, 'tenants', 'created_at'):
                    try:
                        connection.execute(text("""
                            ALTER TABLE tenants
                            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """))
                        connection.commit()
                        logger.info("✅ Added created_at column to tenants table")
                    except Exception as e:
                        logger.error(f"❌ Error adding created_at: {e}")
                        connection.rollback()
                else:
                    logger.info("ℹ️  created_at column already exists")
                
                # Check if updated_at column exists
                if not column_exists(connection, 'tenants', 'updated_at'):
                    try:
                        connection.execute(text("""
                            ALTER TABLE tenants
                            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """))
                        connection.commit()
                        logger.info("✅ Added updated_at column to tenants table")
                    except Exception as e:
                        logger.error(f"❌ Error adding updated_at: {e}")
                        connection.rollback()
                else:
                    logger.info("ℹ️  updated_at column already exists")
                
                logger.info("✅ Tenants table fixed successfully!")
            else:
                logger.info("ℹ️  Using SQLite - no migration needed")
                
    except Exception as e:
        logger.error(f"❌ Error fixing tenants table: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    fix_tenants_table()
