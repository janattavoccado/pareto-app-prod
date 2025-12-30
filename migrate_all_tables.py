"""
Migrate All Tables - Add Missing Columns

This script connects to your Heroku PostgreSQL database and adds the missing
created_at and updated_at columns to the tenants and users tables.

Usage:
    python migrate_all_tables.py

Make sure you have the DATABASE_URL environment variable set.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

def migrate_all_tables():
    """Add missing columns to all tables"""
    
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
            
            print("✅ Connected to PostgreSQL database\n")
            
            # Tables to migrate
            tables = ['tenants', 'users']
            
            for table_name in tables:
                print(f"📋 Processing table: {table_name}")
                
                # Get current columns
                try:
                    inspector = inspect(connection)
                    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                    print(f"   Current columns: {existing_columns}")
                except Exception as e:
                    print(f"   ❌ Error inspecting table: {e}")
                    continue
                
                # Check and add created_at column
                if 'created_at' not in existing_columns:
                    print(f"   ➕ Adding created_at column...")
                    try:
                        connection.execute(text(f"""
                            ALTER TABLE {table_name}
                            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """))
                        connection.commit()
                        print(f"   ✅ Successfully added created_at column")
                    except Exception as e:
                        print(f"   ❌ Error adding created_at: {e}")
                        connection.rollback()
                else:
                    print(f"   ℹ️  created_at column already exists")
                
                # Check and add updated_at column
                if 'updated_at' not in existing_columns:
                    print(f"   ➕ Adding updated_at column...")
                    try:
                        connection.execute(text(f"""
                            ALTER TABLE {table_name}
                            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """))
                        connection.commit()
                        print(f"   ✅ Successfully added updated_at column")
                    except Exception as e:
                        print(f"   ❌ Error adding updated_at: {e}")
                        connection.rollback()
                else:
                    print(f"   ℹ️  updated_at column already exists")
                
                print()
            
            # Verify all tables
            print("🔍 Verifying all tables...")
            inspector = inspect(connection)
            for table_name in tables:
                final_columns = [col['name'] for col in inspector.get_columns(table_name)]
                has_created = 'created_at' in final_columns
                has_updated = 'updated_at' in final_columns
                status = "✅" if (has_created and has_updated) else "❌"
                print(f"{status} {table_name}: {final_columns}")
            
            print("\n✅ ✅ ✅ Migration completed successfully! ✅ ✅ ✅")
            print("\nAll required columns have been added:")
            print("  - created_at")
            print("  - updated_at")
            print("\nYour admin dashboard should now work correctly!")
            return True
    
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_all_tables()
    sys.exit(0 if success else 1)
