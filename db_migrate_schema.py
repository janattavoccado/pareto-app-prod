"""
Database Schema Migration Script

Upgrades existing SQLite database to add new columns for Base64 token storage.
Handles both fresh database creation and upgrading existing databases.

File location: pareto_agents/db_migrate_schema.py
"""

import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def backup_database(db_path: str = 'configurations/pareto.db') -> str:
    """
    Create a backup of the existing database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Path to the backup file
    """
    if not os.path.exists(db_path):
        logger.info(f"Database doesn't exist yet: {db_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        with open(db_path, 'rb') as src:
            with open(backup_path, 'wb') as dst:
                dst.write(src.read())
        
        logger.info(f"✅ Database backed up to: {backup_path}")
        return backup_path
    
    except Exception as e:
        logger.error(f"❌ Error backing up database: {e}")
        return None


def check_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """
    Check if a column exists in a table.
    
    Args:
        conn: SQLite connection
        table: Table name
        column: Column name
        
    Returns:
        True if column exists, False otherwise
    """
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except Exception as e:
        logger.error(f"Error checking column: {e}")
        return False


def add_column_if_not_exists(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> bool:
    """
    Add a column to a table if it doesn't exist.
    
    Args:
        conn: SQLite connection
        table: Table name
        column: Column name
        column_def: Column definition (e.g., "TEXT")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if check_column_exists(conn, table, column):
            logger.info(f"ℹ️  Column already exists: {table}.{column}")
            return True
        
        cursor = conn.cursor()
        sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"
        cursor.execute(sql)
        conn.commit()
        
        logger.info(f"✅ Added column: {table}.{column}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error adding column {table}.{column}: {e}")
        return False


def migrate_schema_v2(db_path: str = 'configurations/pareto.db', backup: bool = True) -> bool:
    """
    Migrate database schema to v2 (add Base64 token columns).
    
    Args:
        db_path: Path to the database file
        backup: Whether to backup database before migration
        
    Returns:
        True if migration successful, False otherwise
    """
    logger.info("=" * 70)
    logger.info("DATABASE SCHEMA MIGRATION v2")
    logger.info("=" * 70)
    
    # Create backup if database exists
    if backup and os.path.exists(db_path):
        backup_path = backup_database(db_path)
        if not backup_path:
            logger.warning("⚠️  Could not backup database, but continuing...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {db_path}")
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            logger.info("ℹ️  Users table doesn't exist yet - fresh database")
            conn.close()
            return True
        
        logger.info("Found existing users table - upgrading schema...")
        
        # Add new columns to users table
        changes_made = False
        
        # Add google_token_base64 column
        if add_column_if_not_exists(conn, 'users', 'google_token_base64', 'TEXT'):
            changes_made = True
        
        # Add google_token_updated_at column
        if add_column_if_not_exists(conn, 'users', 'google_token_updated_at', 'DATETIME'):
            changes_made = True
        
        # Verify migration
        logger.info("=" * 70)
        logger.info("VERIFYING SCHEMA MIGRATION")
        logger.info("=" * 70)
        
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        logger.info("Users table columns:")
        for col in columns:
            col_id, col_name, col_type, not_null, default, pk = col
            logger.info(f"  - {col_name} ({col_type})")
        
        # Check for required columns
        required_columns = [
            'id', 'tenant_id', 'phone_number', 'first_name', 'last_name',
            'email', 'is_enabled', 'google_token_base64', 'google_token_updated_at',
            'created_at', 'updated_at'
        ]
        
        existing_columns = [col[1] for col in columns]
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"⚠️  Missing columns: {missing_columns}")
            logger.warning("   These columns may need to be added manually")
        else:
            logger.info("✅ All required columns present")
        
        conn.close()
        
        logger.info("=" * 70)
        if changes_made:
            logger.info("✅ SCHEMA MIGRATION COMPLETED")
        else:
            logger.info("ℹ️  SCHEMA ALREADY UP TO DATE")
        logger.info("=" * 70)
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        return False


def reset_database(db_path: str = 'configurations/pareto.db', backup: bool = True) -> bool:
    """
    Reset database by deleting and recreating it.
    WARNING: This will delete all data!
    
    Args:
        db_path: Path to the database file
        backup: Whether to backup database before deletion
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("=" * 70)
    logger.warning("⚠️  DATABASE RESET WARNING")
    logger.warning("This will DELETE all data in the database!")
    logger.info("=" * 70)
    
    # Backup first
    if backup and os.path.exists(db_path):
        backup_path = backup_database(db_path)
        logger.info(f"Backup created at: {backup_path}")
    
    try:
        # Delete database file
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"✅ Deleted database: {db_path}")
        
        # Database will be recreated on next connection
        logger.info("Database will be recreated with fresh schema on next connection")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")
        return False


def show_database_info(db_path: str = 'configurations/pareto.db'):
    """
    Display information about the database.
    
    Args:
        db_path: Path to the database file
    """
    if not os.path.exists(db_path):
        logger.info(f"Database doesn't exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("=" * 70)
        logger.info("DATABASE INFORMATION")
        logger.info("=" * 70)
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        logger.info(f"Tables: {len(tables)}")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"  - {table_name}: {count} rows")
        
        # Get users table info
        if any(t[0] == 'users' for t in tables):
            logger.info("\nUsers table schema:")
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            for col in columns:
                col_id, col_name, col_type, not_null, default, pk = col
                logger.info(f"  - {col_name} ({col_type})")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")


if __name__ == '__main__':
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'migrate':
            logger.info("Running schema migration...")
            success = migrate_schema_v2()
            sys.exit(0 if success else 1)
        
        elif command == 'reset':
            logger.warning("RESETTING DATABASE - ALL DATA WILL BE DELETED!")
            confirm = input("Type 'yes' to confirm: ")
            if confirm.lower() == 'yes':
                success = reset_database()
                sys.exit(0 if success else 1)
            else:
                logger.info("Reset cancelled")
                sys.exit(0)
        
        elif command == 'info':
            show_database_info()
            sys.exit(0)
        
        elif command == 'backup':
            backup_database()
            sys.exit(0)
        
        else:
            logger.error(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python -m pareto_agents.db_migrate_schema migrate  - Migrate schema")
            print("  python -m pareto_agents.db_migrate_schema reset    - Reset database (WARNING!)")
            print("  python -m pareto_agents.db_migrate_schema info     - Show database info")
            print("  python -m pareto_agents.db_migrate_schema backup   - Backup database")
            sys.exit(1)
    
    else:
        # Default: run migration
        logger.info("Running schema migration (default)...")
        success = migrate_schema_v2()
        sys.exit(0 if success else 1)
