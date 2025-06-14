import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId
import secrets
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
            "role": "user",
            "reset_token": None,
            "reset_token_expires": None
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
    
    @staticmethod
    async def create_password_reset_token(email: str) -> Optional[str]:
        """Generate and store a password reset token"""
        user = await UserDatabase.get_user_by_email(email)
        if not user:
            return None
        
        # Generate secure token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        # Store token in database
        result = await mongodb.database.users.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires": expires_at
                }
            }
        )
        
        if result.modified_count > 0:
            return reset_token
        return None
    
    @staticmethod
    async def verify_reset_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify reset token and return user if valid"""
        user = await mongodb.database.users.find_one({
            "reset_token": token,
            "reset_token_expires": {"$gt": datetime.utcnow()}
        })
        
        if user:
            user["id"] = str(user["_id"])
            user["_id"] = str(user["_id"])
        
        return user
    
    @staticmethod
    async def reset_password(token: str, new_password_hash: str) -> bool:
        """Reset password using valid token"""
        # Verify token is valid
        user = await UserDatabase.verify_reset_token(token)
        if not user:
            return False
        
        # Update password and clear reset token
        result = await mongodb.database.users.update_one(
            {"_id": ObjectId(user["id"])},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "last_login": datetime.utcnow()
                },
                "$unset": {
                    "reset_token": "",
                    "reset_token_expires": ""
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    async def clear_expired_reset_tokens():
        """Clean up expired reset tokens"""
        await mongodb.database.users.update_many(
            {"reset_token_expires": {"$lt": datetime.utcnow()}},
            {
                "$unset": {
                    "reset_token": "",
                    "reset_token_expires": ""
                }
            }
        )
    
    @staticmethod
    async def delete_user_account(user_id: str) -> bool:
        """Delete a user account by ID"""
        result = await mongodb.database.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count == 1