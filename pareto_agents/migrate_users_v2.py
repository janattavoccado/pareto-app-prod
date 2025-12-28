"""
User Migration Script v2 - JSON to SQLite with Base64 Tokens

Migrates users from users.json to SQLite database with Base64 encoded tokens.
Replaces file-based token storage with database-backed Base64 storage.

File location: pareto_agents/migrate_users_v2.py
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

from .database import get_db_session, Administrator, Tenant, User
from .token_manager import TokenManager
from .auth import PasswordManager

logger = logging.getLogger(__name__)


def migrate_users_from_json_v2(dry_run: bool = False, users_json_path: str = 'configurations/users.json') -> bool:
    """
    Migrate users from users.json to SQLite with Base64 tokens
    
    Args:
        dry_run: If True, preview migration without making changes
        users_json_path: Path to users.json file
        
    Returns:
        True if migration successful, False otherwise
    """
    logger.info("=" * 70)
    logger.info("STARTING USER MIGRATION: JSON → SQLite (Base64 Tokens)")
    logger.info("=" * 70)
    
    # Check if users.json exists
    if not os.path.exists(users_json_path):
        logger.warning(f"⚠️  users.json not found at {users_json_path}")
        return False
    
    try:
        # Load users from JSON
        with open(users_json_path, 'r') as f:
            config = json.load(f)
        
        users_data = config.get('users', [])
        logger.info(f"✅ Loaded {len(users_data)} users from {users_json_path}")
        
        if dry_run:
            logger.info("📋 DRY RUN MODE - No changes will be made")
        
        # Get database session
        session = get_db_session()
        
        try:
            # Create default admin if not exists
            admin = session.query(Administrator).filter_by(username='admin').first()
            if not admin and not dry_run:
                admin = Administrator(
                    username='admin',
                    email='admin@avoccado.tech',
                    password_hash=PasswordManager.hash_password('admin123'),
                    full_name='Administrator',
                    is_active=True
                )
                session.add(admin)
                session.commit()
                logger.info("✅ Created default admin user: admin")
            elif admin:
                logger.info("ℹ️  Admin user already exists")
            else:
                logger.info("📋 [DRY RUN] Would create default admin user")
            
            # Create default tenant if not exists
            tenant = session.query(Tenant).filter_by(company_slug='avoccado-tech').first()
            if not tenant and not dry_run:
                tenant = Tenant(
                    company_name='AVOCCADO Tech',
                    company_slug='avoccado-tech',
                    email='info@avoccado.tech',
                    phone='+46735408023',
                    is_active=True,
                    created_by_admin_id=admin.id if admin else 1
                )
                session.add(tenant)
                session.commit()
                logger.info("✅ Created default tenant: AVOCCADO Tech")
            elif tenant:
                logger.info("ℹ️  Tenant already exists")
            else:
                logger.info("📋 [DRY RUN] Would create default tenant")
            
            # Migrate users
            token_manager = TokenManager()
            migrated_count = 0
            failed_count = 0
            
            for user_data in users_data:
                try:
                    phone_number = user_data.get('phone_number')
                    first_name = user_data.get('first_name', 'Unknown')
                    last_name = user_data.get('last_name', 'User')
                    email = user_data.get('email')
                    enabled = user_data.get('enabled', True)
                    google_token_path = user_data.get('google_token_path')
                    
                    # Check if user already exists
                    existing_user = session.query(User).filter_by(
                        tenant_id=tenant.id if tenant else 1,
                        phone_number=phone_number
                    ).first()
                    
                    if existing_user and not dry_run:
                        logger.info(f"ℹ️  User already exists: {first_name} {last_name} ({phone_number})")
                        continue
                    
                    # Load and encode Google token
                    google_token_base64 = None
                    if google_token_path:
                        try:
                            full_token_path = os.path.join('configurations', google_token_path)
                            if os.path.exists(full_token_path):
                                google_token_base64 = token_manager.encode_from_file(full_token_path)
                                logger.info(f"  ✅ Encoded Google token from: {google_token_path}")
                            else:
                                logger.warning(f"  ⚠️  Token file not found: {full_token_path}")
                        except Exception as e:
                            logger.warning(f"  ⚠️  Could not encode token: {e}")
                    
                    # Create user
                    if not dry_run:
                        new_user = User(
                            tenant_id=tenant.id if tenant else 1,
                            phone_number=phone_number,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            is_enabled=enabled,
                            google_token_base64=google_token_base64
                        )
                        session.add(new_user)
                        session.commit()
                    
                    logger.info(f"✅ Migrated user: {first_name} {last_name} ({phone_number})")
                    migrated_count += 1
                
                except Exception as e:
                    logger.error(f"❌ Error migrating user: {e}")
                    failed_count += 1
                    if not dry_run:
                        session.rollback()
            
            logger.info(f"✅ Successfully migrated {migrated_count} users")
            if failed_count > 0:
                logger.warning(f"⚠️  Failed to migrate {failed_count} users")
            
            # Verify migration
            logger.info("=" * 70)
            logger.info("VERIFYING MIGRATION")
            logger.info("=" * 70)
            
            admin_count = session.query(Administrator).count()
            tenant_count = session.query(Tenant).count()
            user_count = session.query(User).count()
            
            logger.info(f"Administrators in database: {admin_count}")
            logger.info(f"Tenants in database: {tenant_count}")
            logger.info(f"Users in database: {user_count}")
            
            # Show user details
            users = session.query(User).all()
            for user in users:
                token_status = "✅ Has token" if user.has_google_token() else "❌ No token"
                logger.info(f"  - {user.full_name} ({user.phone_number}) - Enabled: {user.is_enabled} - {token_status}")
            
            logger.info("=" * 70)
            logger.info("✅ VERIFICATION COMPLETE")
            logger.info("=" * 70)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Migration error: {e}")
            session.rollback()
            return False
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"❌ Error reading users.json: {e}")
        return False


def verify_migration_v2() -> bool:
    """
    Verify that migration was successful
    
    Returns:
        True if migration is valid, False otherwise
    """
    logger.info("Verifying migration...")
    
    session = get_db_session()
    try:
        admin_count = session.query(Administrator).count()
        tenant_count = session.query(Tenant).count()
        user_count = session.query(User).count()
        
        if admin_count == 0:
            logger.error("❌ No administrators found")
            return False
        
        if tenant_count == 0:
            logger.error("❌ No tenants found")
            return False
        
        if user_count == 0:
            logger.error("❌ No users found")
            return False
        
        logger.info(f"✅ Migration verified: {admin_count} admins, {tenant_count} tenants, {user_count} users")
        return True
    
    except Exception as e:
        logger.error(f"❌ Verification error: {e}")
        return False
    
    finally:
        session.close()


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import sys
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    # Run migration
    success = migrate_users_from_json_v2(dry_run=dry_run)
    
    if success:
        logger.info("✅ Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed")
        sys.exit(1)
