'''
Admin Password Reset Script

This script allows resetting the admin password directly in the database.

Instructions:
1. Run this script from the root of the project.
2. Follow the prompts to enter a new password.
3. The script will update the admin password in the database.
'''

import getpass
import logging
from pareto_agents.database import get_db_session, Administrator
from pareto_agents.auth import PasswordManager

logger = logging.getLogger(__name__)

def reset_admin_password():
    '''Resets the admin password in the database.'''
    session = get_db_session()
    try:
        admin = session.query(Administrator).filter_by(username='admin').first()
        if not admin:
            logger.error("❌ Admin user not found.")
            return

        new_password = getpass.getpass("Enter new password for admin: ")
        if not new_password:
            logger.error("❌ Password cannot be empty.")
            return

        password_hash = PasswordManager.hash_password(new_password)
        admin.password_hash = password_hash
        session.commit()
        logger.info("✅ Admin password has been reset successfully.")

    except Exception as e:
        logger.error(f"❌ An error occurred: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    reset_admin_password()
