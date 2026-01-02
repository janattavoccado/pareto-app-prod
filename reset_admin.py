#!/usr/bin/env python3
"""
Admin Password Reset Script for Pareto App

This script resets the admin password or creates a new admin user.
It can be run locally or on Heroku.

Usage:
    Heroku: heroku run python reset_admin.py --app pareto-app-prod

The script will automatically detect the DATABASE_URL environment variable.
"""

import os
import sys
import logging
import getpass

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
        sys.exit(1)
    
    # Heroku uses 'postgres://' but SQLAlchemy requires 'postgresql://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        import bcrypt
    except ImportError:
        logger.info("Installing bcrypt...")
        os.system('pip install bcrypt')
        import bcrypt
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def run_admin_reset():
    """Reset admin password or create new admin"""
    
    try:
        import psycopg2
    except ImportError:
        logger.info("Installing psycopg2-binary...")
        os.system('pip install psycopg2-binary')
        import psycopg2
    
    database_url = get_database_url()
    logger.info("🔗 Connecting to PostgreSQL database...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database successfully!")
        
        # Check existing admins
        cursor.execute("SELECT id, username, email, is_active FROM administrators")
        admins = cursor.fetchall()
        
        if admins:
            logger.info(f"\n📋 Existing administrators ({len(admins)}):")
            for admin in admins:
                status = "Active" if admin[3] else "Inactive"
                logger.info(f"   ID: {admin[0]} | Username: {admin[1]} | Email: {admin[2]} | Status: {status}")
            
            print("\n" + "=" * 60)
            print("Options:")
            print("  1. Reset password for existing admin")
            print("  2. Create new admin")
            print("  3. Exit")
            print("=" * 60)
            
            choice = input("Enter your choice (1/2/3): ").strip()
            
            if choice == "1":
                username = input("Enter admin username to reset: ").strip()
                
                # Check if admin exists
                cursor.execute("SELECT id FROM administrators WHERE username = %s", (username,))
                admin = cursor.fetchone()
                
                if not admin:
                    logger.error(f"❌ Admin '{username}' not found!")
                    return
                
                # Get new password
                new_password = input("Enter new password: ").strip()
                if len(new_password) < 6:
                    logger.error("❌ Password must be at least 6 characters!")
                    return
                
                # Hash and update password
                password_hash = hash_password(new_password)
                cursor.execute(
                    "UPDATE administrators SET password_hash = %s WHERE username = %s",
                    (password_hash, username)
                )
                
                logger.info(f"✅ Password reset successfully for admin '{username}'!")
                
            elif choice == "2":
                create_new_admin(cursor)
            else:
                logger.info("Exiting...")
                return
        else:
            logger.warning("⚠️  No administrators found in database!")
            print("\nWould you like to create a new admin? (yes/no)")
            if input().strip().lower() in ['yes', 'y']:
                create_new_admin(cursor)
            else:
                logger.info("Exiting...")
                return
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


def create_new_admin(cursor):
    """Create a new admin user"""
    print("\n" + "=" * 60)
    print("Create New Administrator")
    print("=" * 60)
    
    username = input("Username: ").strip()
    if not username:
        logger.error("❌ Username cannot be empty!")
        return
    
    email = input("Email: ").strip()
    if not email or '@' not in email:
        logger.error("❌ Invalid email!")
        return
    
    full_name = input("Full Name (optional): ").strip() or username
    
    password = input("Password (min 6 characters): ").strip()
    if len(password) < 6:
        logger.error("❌ Password must be at least 6 characters!")
        return
    
    # Check if username or email already exists
    cursor.execute(
        "SELECT id FROM administrators WHERE username = %s OR email = %s",
        (username, email)
    )
    if cursor.fetchone():
        logger.error("❌ Username or email already exists!")
        return
    
    # Hash password and create admin
    password_hash = hash_password(password)
    
    cursor.execute("""
        INSERT INTO administrators (username, email, password_hash, full_name, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
        RETURNING id
    """, (username, email, password_hash, full_name))
    
    admin_id = cursor.fetchone()[0]
    logger.info(f"✅ Administrator created successfully!")
    logger.info(f"   ID: {admin_id}")
    logger.info(f"   Username: {username}")
    logger.info(f"   Email: {email}")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Pareto App - Admin Password Reset Script")
    logger.info("=" * 60)
    run_admin_reset()
