"""
Migrate Tenants Table - Add Missing Columns

This script connects to your Heroku PostgreSQL database and adds the missing
created_at and updated_at columns to the tenants table.

Usage:
    python migrate_tenants_columns.py

Make sure you have the DATABASE_URL environment variable set, or it will use
the local SQLite database by default.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

def migrate_tenants_table():
    """Add missing columns to tenants table"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("Please set the DATABASE_URL environment variable before running this script.")
        print("\nFor Heroku, you can get the URL with:")
        print("  heroku config:get DATABASE_URL --app pareto-app-prod")
        sys.exit(1)
    
    # Fix Heroku's old postgres URL scheme
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔧 Connecting to database: {database_url[:50]}...")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Check if we're using PostgreSQL
            if 'postgresql' not in database_url and 'postgres' not in database_url:
                print("ℹ️  Using SQLite - no migration needed")
                return True
            
            print("✅ Connected to PostgreSQL database")
            
            # Get current columns
            inspector = inspect(connection)
            existing_columns = [col['name'] for col in inspector.get_columns('tenants')]
            print(f"📋 Current tenants columns: {existing_columns}")
            
            # Check and add created_at column
            if 'created_at' not in existing_columns:
                print("➕ Adding created_at column...")
                try:
                    connection.execute(text("""
                        ALTER TABLE tenants
                        ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    connection.commit()
                    print("✅ Successfully added created_at column")
                except Exception as e:
                    print(f"❌ Error adding created_at: {e}")
                    connection.rollback()
                    return False
            else:
                print("ℹ️  created_at column already exists")
            
            # Check and add updated_at column
            if 'updated_at' not in existing_columns:
                print("➕ Adding updated_at column...")
                try:
                    connection.execute(text("""
                        ALTER TABLE tenants
                        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    connection.commit()
                    print("✅ Successfully added updated_at column")
                except Exception as e:
                    print(f"❌ Error adding updated_at: {e}")
                    connection.rollback()
                    return False
            else:
                print("ℹ️  updated_at column already exists")
            
            # Verify the columns
            print("\n🔍 Verifying columns...")
            inspector = inspect(connection)
            final_columns = [col['name'] for col in inspector.get_columns('tenants')]
            print(f"📋 Final tenants columns: {final_columns}")
            
            if 'created_at' in final_columns and 'updated_at' in final_columns:
                print("\n✅ ✅ ✅ Migration completed successfully! ✅ ✅ ✅")
                print("\nThe tenants table now has the required columns:")
                print("  - created_at")
                print("  - updated_at")
                print("\nYour admin dashboard should now work correctly!")
                return True
            else:
                print("\n❌ Migration failed - columns not found after migration")
                return False
    
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_tenants_table()
    sys.exit(0 if success else 1)
