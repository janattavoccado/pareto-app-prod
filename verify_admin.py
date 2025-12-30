'''
Script to verify and create the admin user in Heroku PostgreSQL if it does not exist.
'''
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# We need to import the models and password manager from the user's actual code
# This assumes the script is run from the root of the project
from pareto_agents.database import Administrator, Base
from pareto_agents.auth import PasswordManager

# --- Configuration ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Rakmackan#1"  # The password we've been trying to set


def verify_and_create_admin():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set.")
        return

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    print("🚀 Connecting to the database...")
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        print(f"🔍 Checking for administrator: '{ADMIN_USERNAME}'...")
        admin = session.query(Administrator).filter_by(username=ADMIN_USERNAME).first()

        if admin:
            print(f"✅ Administrator '{ADMIN_USERNAME}' already exists.")
            # For good measure, let's ensure the password is correct
            print("🔄 Updating password to be sure...")
            pwd_manager = PasswordManager()
            admin.password_hash = pwd_manager.hash_password(ADMIN_PASSWORD)
            session.commit()
            print("✅ Password updated successfully.")
        else:
            print(f"⚠️ Administrator '{ADMIN_USERNAME}' not found. Creating now...")
            pwd_manager = PasswordManager()
            hashed_password = pwd_manager.hash_password(ADMIN_PASSWORD)
            
            new_admin = Administrator(
                username=ADMIN_USERNAME,
                password_hash=hashed_password,
                email="admin@example.com",  # Default value
                full_name="Administrator",    # Default value
                is_active=True
            )
            session.add(new_admin)
            session.commit()
            print(f"✅ Successfully created administrator: '{ADMIN_USERNAME}'")

        session.close()

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        if 'relation "administrators" does not exist' in str(e):
            print("\nHint: The 'administrators' table is missing. Run the schema creation command first:")
            print("heroku run \"python -c 'from pareto_agents.database import engine, Base; Base.metadata.create_all(engine, checkfirst=True)'\" --app pareto-app-prod")

if __name__ == "__main__":
    verify_and_create_admin()
