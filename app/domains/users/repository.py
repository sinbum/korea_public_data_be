"""
User repository for MongoDB data access.

Handles user CRUD operations, OAuth account linking, and user profile management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from ...core.database import get_database
from .models import User, UserCreate, SocialUserCreate, UserUpdate, AuthProvider

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data access operations"""

    def __init__(self, db_client: MongoClient = None):
        if db_client is None:
            db_client = get_database()
        self.db = db_client
        self.collection: Collection = self.db.users

        # Skip index creation during initialization for performance
        # Indexes should be created during application startup or database migration
        # self._create_indexes()

    def _create_indexes(self):
        """Create database indexes for user collection"""
        try:
            # Use ensure_index with background=True to avoid blocking
            # Only create if they don't exist
            existing_indexes = [idx['name'] for idx in self.collection.list_indexes()]

            # Unique index on email
            if "email_1" not in existing_indexes:
                self.collection.create_index("email", unique=True, background=True)

            # Compound index for provider + external_id (for OAuth users)
            if "provider_1_external_id_1" not in existing_indexes:
                self.collection.create_index([("provider", 1), ("external_id", 1)], sparse=True, background=True)

            # Index for active users
            if "is_active_1" not in existing_indexes:
                self.collection.create_index("is_active", background=True)

            # Index for email verification status
            if "is_verified_1" not in existing_indexes:
                self.collection.create_index("is_verified", background=True)

        except Exception as e:
            # Log the error but don't fail the repository initialization
            logger.warning(f"Could not create indexes: {e}")

    def _convert_objectid_to_string(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB ObjectId to string for Pydantic models"""
        if "_id" in doc:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
        return doc

    def create_local_user(self, user_create: UserCreate, password_hash: str) -> Optional[User]:
        """Create a new local user with hashed password"""
        try:
            user_data = {
                "email": user_create.email,
                "name": user_create.name,
                "password_hash": password_hash,
                "provider": AuthProvider.LOCAL,
                "external_id": None,
                "profile_image_url": None,
                "profile": {},
                "is_active": True,
                "is_verified": False,
                "is_premium": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": None,
                "consent_marketing": user_create.consent_marketing,
                "consent_data_processing": user_create.consent_data_processing
            }

            result = self.collection.insert_one(user_data)
            user_data["_id"] = result.inserted_id

            return User(**self._convert_objectid_to_string(user_data))
        except DuplicateKeyError:
            return None  # Email already exists
        except Exception as e:
            logger.error(f"Error creating local user: {e}")
            return None

    def create_social_user(self, social_user: SocialUserCreate) -> Optional[User]:
        """Create a new user from OAuth social login"""
        try:
            user_data = {
                "email": social_user.email,
                "name": social_user.name,
                "password_hash": None,  # No password for OAuth users
                "provider": social_user.provider,
                "external_id": social_user.external_id,
                "profile_image_url": social_user.profile_image_url,
                "profile": {},
                "is_active": True,
                "is_verified": True,  # OAuth users are pre-verified
                "is_premium": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "consent_marketing": False,  # Default to False for OAuth
                "consent_data_processing": social_user.consent_data_processing
            }

            result = self.collection.insert_one(user_data)
            user_data["_id"] = result.inserted_id

            return User(**self._convert_objectid_to_string(user_data))
        except DuplicateKeyError:
            return None  # Email already exists
        except Exception as e:
            logger.error(f"Error creating social user: {e}")
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            doc = self.collection.find_one({"email": email})
            if doc:
                return User(**self._convert_objectid_to_string(doc))
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_by_provider_and_external_id(self, provider: AuthProvider, external_id: str) -> Optional[User]:
        """Get user by OAuth provider and external ID"""
        try:
            doc = self.collection.find_one({
                "provider": provider,
                "external_id": external_id
            })
            if doc:
                return User(**self._convert_objectid_to_string(doc))
            return None
        except Exception as e:
            logger.error(f"Error getting user by provider: {e}")
            return None

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(user_id)})
            if doc:
                return User(**self._convert_objectid_to_string(doc))
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user information"""
        try:
            update_data = {}

            if user_update.name is not None:
                update_data["name"] = user_update.name

            if user_update.profile is not None:
                update_data["profile"] = user_update.profile.dict()

            if user_update.consent_marketing is not None:
                update_data["consent_marketing"] = user_update.consent_marketing

            update_data["updated_at"] = datetime.utcnow()

            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return self.get_by_id(user_id)
            return None
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    def link_google_account(self, user_id: str, external_id: str, profile_image_url: Optional[str] = None) -> bool:
        """Link Google account to existing local account"""
        try:
            update_data = {
                "external_id": external_id,
                "updated_at": datetime.utcnow()
            }

            if profile_image_url:
                update_data["profile_image_url"] = profile_image_url

            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error linking Google account: {e}")
            return False

    def unlink_google_account(self, user_id: str) -> bool:
        """Unlink Google account from user"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$unset": {"external_id": "", "profile_image_url": ""}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error unlinking Google account: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        """Delete user (GDPR compliance)"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def get_active_users_count(self) -> int:
        """Get count of active users"""
        try:
            return self.collection.count_documents({"is_active": True})
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 0

    def get_users_by_provider(self, provider: AuthProvider, limit: int = 100) -> List[User]:
        """Get users by authentication provider"""
        try:
            docs = self.collection.find({"provider": provider}).limit(limit)
            return [User(**self._convert_objectid_to_string(doc)) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting users by provider: {e}")
            return []
