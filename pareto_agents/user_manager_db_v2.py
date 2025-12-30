import logging
from typing import Optional, Dict, Any

from .database import get_db_session, User, init_db
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

class UserManagerDB:
    """
    Manages user data and Google tokens using the SQLAlchemy database.
    """
    
    def __init__(self):
        # Ensure the database is initialized (tables created)
        init_db()
        self.token_manager = TokenManager()

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves user data from the database by phone number.
        """
        session = next(get_db_session())
        try:
            user = session.query(User).filter_by(phone_number=phone_number).first()
            if user:
                user_data = {
                    "phone_number": user.phone_number,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "is_enabled": user.is_enabled,
                    "google_token_base64": user.google_token_base64,
                }
                return user_data
            return None
        finally:
            session.close()

    def update_user_token(self, phone_number: str, token_dict: Dict[str, Any]) -> bool:
        """
        Updates the Google token for a user.
        """
        session = next(get_db_session())
        try:
            user = session.query(User).filter_by(phone_number=phone_number).first()
            if user:
                user.google_token_base64 = self.token_manager.encode_token(token_dict)
                session.commit()
                logger.info(f"Successfully updated token for user {phone_number}")
                return True
            logger.warning(f"User not found for token update: {phone_number}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating token for {phone_number}: {e}")
            return False
        finally:
            session.close()

# Singleton instance
_user_manager_db_instance = UserManagerDB()

def get_user_manager_db_v2() -> UserManagerDB:
    """
    Returns the singleton instance of the UserManagerDB.
    """
    return _user_manager_db_instance
