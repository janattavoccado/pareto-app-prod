import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pareto_agents.database import Base, User # Import the target User model

# --- Configuration ---
# Source: Local SQLite database
SQLITE_DB_URL = "sqlite:///pareto.db"

# Target: PostgreSQL database (Heroku DATABASE_URL)
# NOTE: You must set the DATABASE_URL environment variable to your Heroku Postgres URL
# before running this script.
POSTGRES_DB_URL = os.getenv("DATABASE_URL")

if not POSTGRES_DB_URL:
    print("FATAL: DATABASE_URL environment variable is not set.")
    print("Please set it to your Heroku PostgreSQL connection string.")
    sys.exit(1)

# Fix for Heroku's old postgres URL scheme
if POSTGRES_DB_URL.startswith("postgres://"):
    POSTGRES_DB_URL = POSTGRES_DB_URL.replace("postgres://", "postgresql://", 1)

# --- Legacy Model for SQLite Reading ---
# This model is used to read the old SQLite schema which is missing the 'tenant_id' column.
LegacyBase = declarative_base()

class LegacyUser(LegacyBase):
    """Legacy model matching the old SQLite schema."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    is_enabled = Column(Boolean, default=False)
    google_token_base64 = Column(String) # Stores the base64 encoded Google token

# --- Database Engines ---
sqlite_engine = create_engine(SQLITE_DB_URL, connect_args={"check_same_thread": False})
postgres_engine = create_engine(POSTGRES_DB_URL)

# --- Session Factories ---
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

def migrate_users():
    """
    Migrates all User records from the SQLite database to the PostgreSQL database.
    """
    print(f"Starting migration from {SQLITE_DB_URL} to {POSTGRES_DB_URL.split('@')[-1]}...")

    # 1. Ensure the target tables exist in PostgreSQL
    print("Ensuring target tables exist in PostgreSQL...")
    Base.metadata.create_all(postgres_engine)

    # 2. Read data from SQLite using the LegacyUser model
    sqlite_session = SQLiteSession()
    try:
        # We query the LegacyUser model which matches the old SQLite schema
        sqlite_users = sqlite_session.query(LegacyUser).all()
    except Exception as e:
        print(f"ERROR: Could not read from SQLite database. Is 'pareto.db' present and the 'users' table created?")
        print(f"Details: {e}")
        sqlite_session.close()
        return

    if not sqlite_users:
        print("No users found in the SQLite database. Migration complete (nothing to do).")
        sqlite_session.close()
        return

    print(f"Found {len(sqlite_users)} users in SQLite. Starting import to PostgreSQL...")

    # 3. Write data to PostgreSQL
    postgres_session = PostgresSession()
    try:
        for legacy_user in sqlite_users:
            # Create a new User object for the PostgreSQL session (target schema)
            new_user = User(
                # tenant_id is set to None as it didn't exist in the old schema
                tenant_id=None, 
                phone_number=legacy_user.phone_number,
                first_name=legacy_user.first_name,
                last_name=legacy_user.last_name,
                email=legacy_user.email,
                is_enabled=legacy_user.is_enabled,
                google_token_base64=legacy_user.google_token_base64
            )
            # Use merge to handle potential existing records
            postgres_session.merge(new_user)
        
        postgres_session.commit()
        print(f"✅ Successfully migrated {len(sqlite_users)} users to PostgreSQL.")

    except Exception as e:
        postgres_session.rollback()
        print(f"FATAL ERROR during PostgreSQL import: {e}")
        print("Migration failed. Rolling back changes on PostgreSQL.")
        sys.exit(1)
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate_users()
