"""
Database Migration Script: Fix Schema Mismatches

This script fixes schema mismatches between the SQLAlchemy models and the actual database:
1. Adds google_calendar_id column to users table (if missing)
2. Adds entity_type, entity_id, changes columns to audit_logs table (if missing)
3. Handles the tenants.name vs tenants.company_name mismatch

Run this script once after deploying the updated code.

Usage:
    python migrate_fix_schema.py

Or run via Heroku:
    heroku run python migrate_fix_schema.py
"""

import os
import logging
from sqlalchemy import create_engine, text, inspect

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


def column_exists(conn, table_name, column_name, is_postgres):
    """Check if a column exists in a table"""
    if is_postgres:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table AND column_name = :column
        """), {"table": table_name, "column": column_name})
        return result.fetchone() is not None
    else:
        # SQLite
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        return column_name in columns


def run_migration():
    """Run all migrations to fix schema mismatches"""
    database_url = get_database_url()
    is_postgres = 'postgresql' in database_url
    
    logger.info(f"Connecting to {'PostgreSQL' if is_postgres else 'SQLite'} database...")
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        migrations_applied = []
        
        # =====================================================================
        # 1. Fix users table - add google_calendar_id
        # =====================================================================
        if not column_exists(conn, 'users', 'google_calendar_id', is_postgres):
            logger.info("Adding 'google_calendar_id' column to users table...")
            if is_postgres:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_calendar_id VARCHAR(255) NULL"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_calendar_id TEXT NULL"))
            migrations_applied.append("users.google_calendar_id")
        else:
            logger.info("✓ users.google_calendar_id already exists")
        
        # =====================================================================
        # 2. Fix audit_logs table - add missing columns
        # =====================================================================
        if not column_exists(conn, 'audit_logs', 'entity_type', is_postgres):
            logger.info("Adding 'entity_type' column to audit_logs table...")
            if is_postgres:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN entity_type VARCHAR(100) NULL"))
            else:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN entity_type TEXT NULL"))
            migrations_applied.append("audit_logs.entity_type")
        else:
            logger.info("✓ audit_logs.entity_type already exists")
        
        if not column_exists(conn, 'audit_logs', 'entity_id', is_postgres):
            logger.info("Adding 'entity_id' column to audit_logs table...")
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN entity_id INTEGER NULL"))
            migrations_applied.append("audit_logs.entity_id")
        else:
            logger.info("✓ audit_logs.entity_id already exists")
        
        if not column_exists(conn, 'audit_logs', 'changes', is_postgres):
            logger.info("Adding 'changes' column to audit_logs table...")
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN changes TEXT NULL"))
            migrations_applied.append("audit_logs.changes")
        else:
            logger.info("✓ audit_logs.changes already exists")
        
        # =====================================================================
        # 3. Fix tenants table - handle name vs company_name mismatch
        # =====================================================================
        has_name = column_exists(conn, 'tenants', 'name', is_postgres)
        has_company_name = column_exists(conn, 'tenants', 'company_name', is_postgres)
        
        if has_name and not has_company_name:
            # Old schema: has 'name' but not 'company_name'
            # Add company_name as alias/copy of name
            logger.info("Adding 'company_name' column to tenants table (copying from 'name')...")
            if is_postgres:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN company_name VARCHAR(255)"))
                conn.execute(text("UPDATE tenants SET company_name = name"))
            else:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN company_name TEXT"))
                conn.execute(text("UPDATE tenants SET company_name = name"))
            migrations_applied.append("tenants.company_name (copied from name)")
        
        if has_company_name and has_name:
            # Both exist - make sure name is populated from company_name for backwards compat
            logger.info("Syncing 'name' column with 'company_name' in tenants table...")
            conn.execute(text("UPDATE tenants SET name = company_name WHERE name IS NULL OR name = ''"))
            migrations_applied.append("tenants.name synced with company_name")
        
        if has_company_name and not has_name:
            # New schema: has 'company_name' but not 'name'
            # Add 'name' column for backwards compatibility
            logger.info("Adding 'name' column to tenants table (for backwards compatibility)...")
            if is_postgres:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN name VARCHAR(255)"))
                conn.execute(text("UPDATE tenants SET name = company_name"))
                # Make name NOT NULL after populating
                conn.execute(text("ALTER TABLE tenants ALTER COLUMN name SET NOT NULL"))
            else:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN name TEXT"))
                conn.execute(text("UPDATE tenants SET name = company_name"))
            migrations_applied.append("tenants.name (copied from company_name)")
        
        # =====================================================================
        # 4. Fix tenants table - add company_slug if missing
        # =====================================================================
        if not column_exists(conn, 'tenants', 'company_slug', is_postgres):
            logger.info("Adding 'company_slug' column to tenants table...")
            if is_postgres:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN company_slug VARCHAR(255)"))
                # Generate slugs from company_name
                conn.execute(text("""
                    UPDATE tenants 
                    SET company_slug = LOWER(REPLACE(COALESCE(company_name, name, 'tenant-' || id::text), ' ', '-'))
                    WHERE company_slug IS NULL
                """))
            else:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN company_slug TEXT"))
                conn.execute(text("""
                    UPDATE tenants 
                    SET company_slug = LOWER(REPLACE(COALESCE(company_name, name, 'tenant-' || id), ' ', '-'))
                    WHERE company_slug IS NULL
                """))
            migrations_applied.append("tenants.company_slug")
        else:
            logger.info("✓ tenants.company_slug already exists")
        
        # Commit all changes
        conn.commit()
        
        # =====================================================================
        # Summary
        # =====================================================================
        if migrations_applied:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ Migration completed successfully!")
            logger.info("=" * 60)
            logger.info("Columns added/fixed:")
            for m in migrations_applied:
                logger.info(f"  - {m}")
        else:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ No migrations needed - schema is up to date!")
            logger.info("=" * 60)


if __name__ == '__main__':
    run_migration()
