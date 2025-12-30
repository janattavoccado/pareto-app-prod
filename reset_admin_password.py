import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash # Assuming werkzeug is used for hashing

# Import necessary models from the application's database module
try:
    from pareto_agents.database import Base, Administrator
except ImportError:
    print("FATAL: Could not import database models. Ensure you are running this script from the project root.")
    sys.exit(1)

# --- Configuration ---
ADMIN_USERNAME = "admin"
# NOTE: The user MUST change this password before running the script
NEW_PASSWORD = "Rakmackan#1"

# Target: PostgreSQL database (Heroku DATABASE_URL)
POSTGRES_DB_URL = os.getenv("DATABASE_URL")

if not POSTGRES_DB_URL:
    print("FATAL: DATABASE_URL environment variable is not set.")
    print("Please set it to your Heroku PostgreSQL connection string.")
    sys.exit(1)

# Fix for Heroku's old postgres URL scheme
if POSTGRES_DB_URL.startswith("postgres://"):
    POSTGRES_DB_URL = POSTGRES_DB_URL.replace("postgres://", "postgresql://", 1)

# --- Database Engine and Session ---
engine = create_engine(POSTGRES_DB_URL)
Session = sessionmaker(bind=engine)

def reset_password():
    """
    Resets the password for the admin user, creating the user if it doesn't exist.
    """
    print(f"Attempting to connect to database: {POSTGRES_DB_URL.split('@')[-1]}...")

    session = Session()
    try:
        # 1. Ensure the administrators table exists
        Base.metadata.create_all(engine)

        # 2. Hash the new password
        hashed_password = generate_password_hash(NEW_PASSWORD)

        # 3. Find or create the admin user
        admin_user = session.query(Administrator).filter_by(username=ADMIN_USERNAME).first()

        if admin_user:
            # Update existing user
            admin_user.password_hash = hashed_password
            session.commit()
            print(f"✅ Successfully updated password for existing administrator: '{ADMIN_USERNAME}'")
        else:
            # Create new user
            new_admin = Administrator(
                username=ADMIN_USERNAME,
                password_hash=hashed_password,
                is_active=True
            )
            session.add(new_admin)
            session.commit()
            print(f"✅ Successfully created new administrator: '{ADMIN_USERNAME}'")

        print(f"NOTE: The new password is set to: '{NEW_PASSWORD}'")
        print("Please change this password in the script before running it in a real environment.")

    except Exception as e:
        session.rollback()
        print(f"FATAL ERROR during password reset: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    reset_password()
