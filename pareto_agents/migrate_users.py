"""
Migration Script: Import users from users.json to SQLite database

This script:
1. Reads existing users.json file
2. Creates a default tenant (AVOCCADO Tech)
3. Creates a default admin user
4. Imports all users from JSON to SQLite
5. Maintains backward compatibility

File location: pareto_agents/migrate_users.py
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .database import (
    get_db_manager, get_db_session, 
    Administrator, Tenant, User, AuditLog,
    Base
)

logger = logging.getLogger(__name__)


class UserMigrator:
    """Handles migration of users from JSON to SQLite database"""
    
    def __init__(self, json_path: str = "configurations/users.json"):
        """
        Initialize migrator
        
        Args:
            json_path: Path to users.json file
        """
        self.json_path = json_path
        self.users_data: Optional[Dict] = None
        self.db_manager = get_db_manager()
    
    def load_json(self) -> bool:
        """
        Load users from JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.json_path):
                logger.error(f"❌ File not found: {self.json_path}")
                return False
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.users_data = json.load(f)
            
            logger.info(f"✅ Loaded {len(self.users_data.get('users', []))} users from {self.json_path}")
            return True
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {self.json_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error loading JSON: {e}")
            return False
    
    def create_default_admin(self, session) -> Optional[Administrator]:
        """
        Create default admin user if not exists
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Administrator instance or None
        """
        try:
            # Check if admin already exists
            existing_admin = session.query(Administrator).filter_by(username='admin').first()
            if existing_admin:
                logger.info(f"✅ Default admin already exists: {existing_admin.username}")
                return existing_admin
            
            # Import bcrypt for password hashing
            try:
                from bcrypt import hashpw, gensalt
                password_hash = hashpw(b'admin123', gensalt()).decode('utf-8')
            except ImportError:
                logger.warning("⚠️  bcrypt not installed, using plain password (NOT SECURE!)")
                password_hash = 'admin123'
            
            admin = Administrator(
                username='admin',
                email='admin@avoccado.tech',
                password_hash=password_hash,
                full_name='Administrator',
                is_active=True
            )
            
            session.add(admin)
            session.commit()
            
            logger.info(f"✅ Created default admin user: {admin.username}")
            logger.warning("⚠️  DEFAULT CREDENTIALS - CHANGE IMMEDIATELY IN PRODUCTION!")
            logger.warning("   Username: admin")
            logger.warning("   Password: admin123")
            
            return admin
        
        except Exception as e:
            logger.error(f"❌ Error creating default admin: {e}")
            session.rollback()
            return None
    
    def create_default_tenant(self, session, admin: Administrator) -> Optional[Tenant]:
        """
        Create default tenant if not exists
        
        Args:
            session: SQLAlchemy session
            admin: Administrator instance
            
        Returns:
            Tenant instance or None
        """
        try:
            # Check if tenant already exists
            existing_tenant = session.query(Tenant).filter_by(company_slug='avoccado-tech').first()
            if existing_tenant:
                logger.info(f"✅ Default tenant already exists: {existing_tenant.company_name}")
                return existing_tenant
            
            tenant = Tenant(
                company_name='AVOCCADO Tech',
                company_slug='avoccado-tech',
                email='info@avoccado.tech',
                phone='+46735408023',
                is_active=True,
                created_by_admin_id=admin.id
            )
            
            session.add(tenant)
            session.commit()
            
            logger.info(f"✅ Created default tenant: {tenant.company_name}")
            return tenant
        
        except Exception as e:
            logger.error(f"❌ Error creating default tenant: {e}")
            session.rollback()
            return None
    
    def migrate_users(self, tenant: Tenant, session) -> int:
        """
        Migrate users from JSON to database
        
        Args:
            tenant: Tenant instance
            session: SQLAlchemy session
            
        Returns:
            Number of users migrated
        """
        if not self.users_data:
            logger.error("❌ No users data loaded")
            return 0
        
        migrated_count = 0
        users_list = self.users_data.get('users', [])
        
        for user_data in users_list:
            try:
                phone_number = user_data.get('phone_number')
                
                # Check if user already exists
                existing_user = session.query(User).filter_by(
                    tenant_id=tenant.id,
                    phone_number=phone_number
                ).first()
                
                if existing_user:
                    logger.info(f"⚠️  User already exists: {phone_number} (skipping)")
                    continue
                
                # Create new user
                user = User(
                    tenant_id=tenant.id,
                    phone_number=phone_number,
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    email=user_data.get('email'),
                    is_enabled=user_data.get('enabled', True),
                    google_token_path=user_data.get('google_token_path')
                )
                
                session.add(user)
                migrated_count += 1
                
                logger.info(f"✅ Migrated user: {user.full_name} ({phone_number})")
            
            except Exception as e:
                logger.error(f"❌ Error migrating user {user_data.get('phone_number')}: {e}")
                session.rollback()
                continue
        
        # Commit all users at once
        try:
            session.commit()
            logger.info(f"✅ Successfully migrated {migrated_count} users")
        except Exception as e:
            logger.error(f"❌ Error committing users: {e}")
            session.rollback()
            return 0
        
        return migrated_count
    
    def run_migration(self, dry_run: bool = False) -> bool:
        """
        Run complete migration process
        
        Args:
            dry_run: If True, only show what would be migrated without making changes
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("STARTING USER MIGRATION: JSON → SQLite")
        logger.info("=" * 70)
        
        # Load JSON
        if not self.load_json():
            return False
        
        # Get database session
        session = self.db_manager.get_session()
        
        try:
            # Create default admin
            admin = self.create_default_admin(session)
            if not admin:
                logger.error("❌ Failed to create default admin")
                return False
            
            # Create default tenant
            tenant = self.create_default_tenant(session, admin)
            if not tenant:
                logger.error("❌ Failed to create default tenant")
                return False
            
            # Migrate users
            if dry_run:
                logger.info("🔍 DRY RUN MODE - No changes will be made")
                users_list = self.users_data.get('users', [])
                logger.info(f"Would migrate {len(users_list)} users")
                for user_data in users_list:
                    logger.info(f"  - {user_data.get('first_name')} {user_data.get('last_name')} ({user_data.get('phone_number')})")
            else:
                migrated_count = self.migrate_users(tenant, session)
                if migrated_count == 0:
                    logger.warning("⚠️  No users were migrated")
            
            logger.info("=" * 70)
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            return True
        
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    def verify_migration(self) -> bool:
        """
        Verify that migration was successful
        
        Returns:
            True if verification passed, False otherwise
        """
        logger.info("=" * 70)
        logger.info("VERIFYING MIGRATION")
        logger.info("=" * 70)
        
        session = self.db_manager.get_session()
        
        try:
            # Check admins
            admin_count = session.query(Administrator).count()
            logger.info(f"Administrators in database: {admin_count}")
            
            # Check tenants
            tenant_count = session.query(Tenant).count()
            logger.info(f"Tenants in database: {tenant_count}")
            
            # Check users
            user_count = session.query(User).count()
            logger.info(f"Users in database: {user_count}")
            
            # List all users
            users = session.query(User).all()
            for user in users:
                logger.info(f"  - {user.full_name} ({user.phone_number}) - Enabled: {user.is_enabled}")
            
            logger.info("=" * 70)
            logger.info("✅ VERIFICATION COMPLETE")
            logger.info("=" * 70)
            
            return admin_count > 0 and tenant_count > 0 and user_count > 0
        
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
        
        finally:
            session.close()


def migrate_users_from_json(json_path: str = "configurations/users.json", dry_run: bool = False) -> bool:
    """
    Convenience function to run migration
    
    Args:
        json_path: Path to users.json file
        dry_run: If True, only show what would be migrated
        
    Returns:
        True if successful, False otherwise
    """
    migrator = UserMigrator(json_path)
    success = migrator.run_migration(dry_run=dry_run)
    
    if success and not dry_run:
        migrator.verify_migration()
    
    return success


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    import sys
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        logger.info("Running in DRY RUN mode (no changes will be made)")
    
    success = migrate_users_from_json(dry_run=dry_run)
    sys.exit(0 if success else 1)
