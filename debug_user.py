#!/usr/bin/env python3
"""
Debug script to check user data in the database

Usage:
    heroku run python debug_user.py --app pareto-app-prod
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment variable"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable is not set!")
        sys.exit(1)
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url


def debug_users():
    """Debug user data in the database"""
    
    try:
        import psycopg2
    except ImportError:
        os.system('pip install psycopg2-binary')
        import psycopg2
    
    database_url = get_database_url()
    logger.info("🔗 Connecting to PostgreSQL database...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database successfully!")
        
        # Get all users
        logger.info("\n📋 All users in database:")
        cursor.execute("""
            SELECT id, phone_number, first_name, last_name, email, is_enabled, 
                   tenant_id, google_token_base64 IS NOT NULL as has_token
            FROM users
            ORDER BY id
        """)
        
        users = cursor.fetchall()
        
        if not users:
            logger.info("   No users found in database!")
        else:
            for user in users:
                logger.info(f"""
   User ID: {user[0]}
   Phone: '{user[1]}' (length: {len(user[1]) if user[1] else 0})
   Name: {user[2]} {user[3]}
   Email: {user[4]}
   Enabled: {user[5]}
   Tenant ID: {user[6]}
   Has Token: {user[7]}
   ---""")
        
        # Test phone number lookup
        test_phone = "+46735408023"
        logger.info(f"\n🔍 Testing phone lookup for: '{test_phone}'")
        
        cursor.execute("""
            SELECT id, phone_number, is_enabled FROM users WHERE phone_number = %s
        """, (test_phone,))
        
        result = cursor.fetchone()
        if result:
            logger.info(f"   ✅ Found user: ID={result[0]}, Phone='{result[1]}', Enabled={result[2]}")
        else:
            logger.info(f"   ❌ No user found with exact phone number '{test_phone}'")
            
            # Try partial match
            logger.info(f"\n🔍 Trying partial match (LIKE '%46735408023%')...")
            cursor.execute("""
                SELECT id, phone_number, is_enabled FROM users WHERE phone_number LIKE %s
            """, ('%46735408023%',))
            
            results = cursor.fetchall()
            if results:
                for r in results:
                    logger.info(f"   Found: ID={r[0]}, Phone='{r[1]}', Enabled={r[2]}")
            else:
                logger.info("   No partial matches found either")
        
        # Check tenants
        logger.info("\n📋 All tenants in database:")
        cursor.execute("""
            SELECT id, name, company_name, is_active
            FROM tenants
            ORDER BY id
        """)
        
        tenants = cursor.fetchall()
        if not tenants:
            logger.info("   No tenants found in database!")
        else:
            for tenant in tenants:
                logger.info(f"   Tenant ID: {tenant[0]}, Name: {tenant[1]}, Company: {tenant[2]}, Active: {tenant[3]}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ Debug completed!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Pareto App - User Debug Script")
    logger.info("=" * 60)
    debug_users()
