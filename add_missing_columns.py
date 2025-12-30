'''
Script to add all potentially missing columns to the administrators table in Heroku PostgreSQL.
'''
import os
from sqlalchemy import create_engine, text

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set.")
    exit()

# Fix for Heroku's old postgres URL scheme
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# A comprehensive list of columns that might be missing
COLUMNS_TO_ADD = {
    "administrators": [
        ("full_name", "VARCHAR"),
        ("email", "VARCHAR"),
        ("last_login_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP"),
        ("updated_at", "TIMESTAMP")
    ],
    "admin_sessions": [
        ("ip_address", "VARCHAR"),
        ("user_agent", "VARCHAR"),
        ("is_active", "BOOLEAN")
    ],
    "audit_logs": [
        ("ip_address", "VARCHAR"),
        ("user_agent", "VARCHAR")
    ]
}

def add_all_missing_columns():
    print("🚀 Connecting to the database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            for table, columns in COLUMNS_TO_ADD.items():
                for column, col_type in columns:
                    command = f"ALTER TABLE {table} ADD COLUMN {column} {col_type};"
                    try:
                        print(f"Executing: {command}")
                        # Use a transaction for each command
                        trans = connection.begin()
                        connection.execute(text(command))
                        trans.commit()
                        print(f"✅ Successfully executed.")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"⚠️  Column '{column}' in table '{table}' already exists, skipping.")
                        else:
                            print(f"❌ Error executing command: {command}")
                            print(f"   Details: {e}")
                            # Rollback the failed transaction
                            if 'trans' in locals() and trans.is_active:
                                trans.rollback()
            
        print("\n🎉 All missing columns checked and added successfully!")
    except Exception as e:
        print(f"\n❌ An error occurred during the process: {e}")

if __name__ == "__main__":
    add_all_missing_columns()
