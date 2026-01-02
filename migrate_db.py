#!/usr/bin/env python3
"""
Database Migration Script for Pareto App

This script fixes schema mismatches between the SQLAlchemy models and the PostgreSQL database.
It can be run locally or on Heroku.

Usage:
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
    """Run database migration to fix schema mismatches"""
    
    try:
        import psycopg2
    except ImportError:
        logger.info("Installing psycopg2-binary...")
        os.system('pip install psycopg2-binary')
        import psycopg2
    
    database_url = get_database_url()
    logger.info("🔗 Connecting to PostgreSQL database...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database successfully!")
        
        # First, let's check what columns exist in each table
        logger.info("\n📊 Checking current table schemas...")
        
        tables_to_check = ['administrators', 'tenants', 'users', 'admin_sessions', 'audit_logs']
        
        for table in tables_to_check:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = [row[0] for row in cursor.fetchall()]
            if columns:
                logger.info(f"   {table}: {', '.join(columns)}")
            else:
                logger.info(f"   {table}: TABLE DOES NOT EXIST")
        
        # Define the expected schema for each table
        # We'll add missing columns or rename existing ones
        
        migrations = []
        
        # ============================================
        # ADMINISTRATORS TABLE MIGRATIONS
        # ============================================
        
        # Check if last_login_at exists and needs to be renamed to last_login
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'administrators' AND column_name = 'last_login_at'
        """)
        if cursor.fetchone():
            migrations.append({
                'name': 'Rename last_login_at to last_login in administrators',
                'sql': "ALTER TABLE administrators RENAME COLUMN last_login_at TO last_login"
            })
        else:
            # Check if last_login exists
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'administrators' AND column_name = 'last_login'
            """)
            if not cursor.fetchone():
                migrations.append({
                    'name': 'Add last_login column to administrators',
                    'sql': "ALTER TABLE administrators ADD COLUMN last_login TIMESTAMP"
                })
        
        # ============================================
        # TENANTS TABLE MIGRATIONS
        # ============================================
        
        # Check if tenants table exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'tenants'
        """)
        tenant_columns = [row[0] for row in cursor.fetchall()]
        
        if not tenant_columns:
            # Create tenants table from scratch
            migrations.append({
                'name': 'Create tenants table',
                'sql': """
                    CREATE TABLE IF NOT EXISTS tenants (
                        id SERIAL PRIMARY KEY,
                        company_name VARCHAR(255) NOT NULL,
                        company_slug VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255),
                        phone VARCHAR(20),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by_admin_id INTEGER REFERENCES administrators(id)
                    )
                """
            })
        else:
            # Check for missing columns and add them
            required_columns = {
                'company_name': "ALTER TABLE tenants ADD COLUMN company_name VARCHAR(255)",
                'company_slug': "ALTER TABLE tenants ADD COLUMN company_slug VARCHAR(255)",
                'email': "ALTER TABLE tenants ADD COLUMN email VARCHAR(255)",
                'phone': "ALTER TABLE tenants ADD COLUMN phone VARCHAR(20)",
                'is_active': "ALTER TABLE tenants ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
                'created_at': "ALTER TABLE tenants ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                'updated_at': "ALTER TABLE tenants ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                'created_by_admin_id': "ALTER TABLE tenants ADD COLUMN created_by_admin_id INTEGER"
            }
            
            for col, sql in required_columns.items():
                if col not in tenant_columns:
                    migrations.append({
                        'name': f'Add {col} column to tenants',
                        'sql': sql
                    })
            
            # Check for column renames (e.g., name -> company_name)
            if 'name' in tenant_columns and 'company_name' not in tenant_columns:
                migrations.append({
                    'name': 'Rename name to company_name in tenants',
                    'sql': "ALTER TABLE tenants RENAME COLUMN name TO company_name"
                })
            
            if 'slug' in tenant_columns and 'company_slug' not in tenant_columns:
                migrations.append({
                    'name': 'Rename slug to company_slug in tenants',
                    'sql': "ALTER TABLE tenants RENAME COLUMN slug TO company_slug"
                })
        
        # ============================================
        # USERS TABLE MIGRATIONS
        # ============================================
        
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        user_columns = [row[0] for row in cursor.fetchall()]
        
        if user_columns:
            user_required_columns = {
                'google_token_base64': "ALTER TABLE users ADD COLUMN google_token_base64 TEXT",
                'google_token_updated_at': "ALTER TABLE users ADD COLUMN google_token_updated_at TIMESTAMP",
                'tenant_id': "ALTER TABLE users ADD COLUMN tenant_id INTEGER",
                'phone_number': "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)",
                'first_name': "ALTER TABLE users ADD COLUMN first_name VARCHAR(255)",
                'last_name': "ALTER TABLE users ADD COLUMN last_name VARCHAR(255)",
                'email': "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
                'is_enabled': "ALTER TABLE users ADD COLUMN is_enabled BOOLEAN DEFAULT TRUE",
                'created_at': "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                'updated_at': "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }
            
            for col, sql in user_required_columns.items():
                if col not in user_columns:
                    migrations.append({
                        'name': f'Add {col} column to users',
                        'sql': sql
                    })
        
        # ============================================
        # RUN MIGRATIONS
        # ============================================
        
        if migrations:
            logger.info(f"\n🔧 Running {len(migrations)} migrations...")
            
            for migration in migrations:
                logger.info(f"   📋 {migration['name']}")
                try:
                    cursor.execute(migration['sql'])
                    logger.info(f"      ✅ Success")
                except psycopg2.Error as e:
                    logger.warning(f"      ⚠️  Skipped (may already exist): {str(e).split(chr(10))[0]}")
        else:
            logger.info("\n✅ No migrations needed - schema is up to date!")
        
        # ============================================
        # VERIFY FINAL SCHEMA
        # ============================================
        
        logger.info("\n📊 Final table schemas:")
        
        for table in tables_to_check:
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = cursor.fetchall()
            if columns:
                logger.info(f"\n   {table}:")
                for col in columns:
                    logger.info(f"      - {col[0]}: {col[1]}")
        
        # ============================================
        # CHECK DATA COUNTS
        # ============================================
        
        logger.info("\n📈 Data counts:")
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"   {table}: {count} records")
            except:
                logger.info(f"   {table}: N/A")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ Migration completed successfully!")
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Pareto App - Database Migration Script")
    logger.info("=" * 60)
    run_migration()
