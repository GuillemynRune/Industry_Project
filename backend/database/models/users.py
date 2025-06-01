import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from ..connection import mongodb

logger = logging.getLogger(__name__)

class UserDatabase:
    """User database operations"""
    
    @staticmethod
    async def create_user(email: str, password_hash: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user"""
        # Check if user exists
        if await mongodb.database.users.find_one({"email": email}):
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
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        user = await mongodb.database.users.find_one({"email": email})
        if user:
            user["id"] = str(user["_id"])
            user["_id"] = str(user["_id"])
        return user
    
    @staticmethod
    async def update_last_login(email: str) -> bool:
        """Update user's last login timestamp"""
        result = await mongodb.database.users.update_one(
            {"email": email},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        return result.modified_count > 0