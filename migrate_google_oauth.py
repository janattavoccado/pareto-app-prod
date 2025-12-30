import os
import psycopg2
from psycopg2 import sql

def migrate_google_oauth_table():
    """Connects to the database and adds the google_oauth_credentials table."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable not set.")
        return

    print(f"🔧 Connecting to database: {db_url[:30]}...")

    try:
        conn = psycopg2.connect(db_url)
        print("✅ Connected to PostgreSQL database")
        
        with conn.cursor() as cur:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'google_oauth_credentials'
                );
            """)
            table_exists = cur.fetchone()[0]

            if table_exists:
                print("ℹ️  google_oauth_credentials table already exists")
            else:
                print("➕ Creating google_oauth_credentials table...")
                cur.execute("""
                    CREATE TABLE google_oauth_credentials (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                        credentials_json TEXT NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
                    );
                """)
                conn.commit()
                print("✅ Successfully created google_oauth_credentials table")

        print("\n✅ ✅ ✅ Migration completed successfully! ✅ ✅ ✅")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_google_oauth_table()
