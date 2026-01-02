#!/usr/bin/env python3
"""
Database Migration Script for Pareto App

This script adds missing columns to the PostgreSQL database.
It can be run locally or on Heroku.

Usage:
    Local:  python migrate_db.py
    Heroku: heroku run python migrate_db.py --app pareto-app-prod

The script will automatically detect the DATABASE_URL environment variable.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment variable"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable is not set!")
        logger.error("Please set it before running this script:")
        logger.error("  export DATABASE_URL='postgres://user:password@host:port/database'")
        sys.exit(1)
    
    # Heroku uses 'postgres://' but SQLAlchemy requires 'postgresql://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url


def run_migration():
    """Run database migration to add missing columns"""
    
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        logger.error("❌ psycopg2 is not installed. Installing...")
        os.system('pip install psycopg2-binary')
        import psycopg2
        from psycopg2 import sql
    
    database_url = get_database_url()
    logger.info("🔗 Connecting to PostgreSQL database...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database successfully!")
        
        # List of migrations to run
        migrations = [
            {
                'name': 'Add google_token_updated_at column to users table',
                'check': """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_token_updated_at'
                """,
                'sql': """
                    ALTER TABLE users 
                    ADD COLUMN google_token_updated_at TIMESTAMP
                """
            },
            {
                'name': 'Add google_token_base64 column to users table (if missing)',
                'check': """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_token_base64'
                """,
                'sql': """
                    ALTER TABLE users 
                    ADD COLUMN google_token_base64 TEXT
                """
            }
        ]
        
        # Run each migration
        for migration in migrations:
            logger.info(f"📋 Checking: {migration['name']}")
            
            # Check if column already exists
            cursor.execute(migration['check'])
            result = cursor.fetchone()
            
            if result:
                logger.info(f"   ⏭️  Already exists, skipping...")
            else:
                logger.info(f"   🔧 Applying migration...")
                try:
                    cursor.execute(migration['sql'])
                    logger.info(f"   ✅ Migration applied successfully!")
                except psycopg2.Error as e:
                    logger.error(f"   ❌ Migration failed: {e}")
        
        # Verify the schema
        logger.info("\n📊 Verifying users table schema...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        logger.info("   Users table columns:")
        for col in columns:
            logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # Check if users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"\n📈 Total users in database: {user_count}")
        
        # Check if tenants exist
        cursor.execute("SELECT COUNT(*) FROM tenants")
        tenant_count = cursor.fetchone()[0]
        logger.info(f"📈 Total tenants in database: {tenant_count}")
        
        # Check if administrators exist
        cursor.execute("SELECT COUNT(*) FROM administrators")
        admin_count = cursor.fetchone()[0]
        logger.info(f"📈 Total administrators in database: {admin_count}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ Migration completed successfully!")
        
        if user_count == 0:
            logger.warning("\n⚠️  No users found in database!")
            logger.warning("   You need to add users through the admin dashboard.")
        
        if tenant_count == 0:
            logger.warning("\n⚠️  No tenants found in database!")
            logger.warning("   You need to add tenants through the admin dashboard first.")
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Pareto App - Database Migration Script")
    logger.info("=" * 60)
    run_migration()
