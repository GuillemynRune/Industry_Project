import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from database.connection import mongodb

logger = logging.getLogger(__name__)

class UserDatabase:
    """User database operations"""
    
    @staticmethod
    async def create_user(email: str, password_hash: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await mongodb.database.users.find_one({"email": email})
            if existing_user:
                return {"success": False, "message": "Email already registered"}
            
            user_doc = {
                "email": email,
                "password_hash": password_hash,
                "display_name": display_name or "Anonymous",
                "created_at": datetime.utcnow(),
                "last_login": None,
                "is_active": True,
                "role": "user"
            }
            
            result = await mongodb.database.users.insert_one(user_doc)
            
            return {
                "success": True,
                "message": "User created successfully",
                "user_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {"success": False, "message": "Failed to create user"}
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            user = await mongodb.database.users.find_one({"email": email})
            if user:
                user["id"] = str(user["_id"])
                del user["_id"]
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = await mongodb.database.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user["_id"])
                del user["_id"]
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    async def update_last_login(email: str) -> bool:
        """Update user's last login timestamp"""
        try:
            result = await mongodb.database.users.update_one(
                {"email": email},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    @staticmethod
    async def deactivate_user(email: str) -> bool:
        """Deactivate user account"""
        try:
            result = await mongodb.database.users.update_one(
                {"email": email},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False
    
    @staticmethod
    async def update_user_profile(email: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            # Only allow certain fields to be updated
            allowed_fields = {"display_name", "role"}
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                return False
            
            result = await mongodb.database.users.update_one(
                {"email": email},
                {"$set": filtered_updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False