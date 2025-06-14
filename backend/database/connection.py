import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "postnatal_stories"

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI environment variable not set")
        
    mongodb.client = AsyncIOMotorClient(MONGODB_URI)
    mongodb.database = mongodb.client[DATABASE_NAME]
    
    await mongodb.client.admin.command('ping')
    logger.info("Connected to MongoDB successfully!")
    
    await create_indexes()
    return True

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes"""
    try:        
        await mongodb.database.users.create_index([("email", 1)], unique=True)
        await mongodb.database.pending_stories.create_index([("status", 1), ("created_at", 1)])
        await mongodb.database.approved_stories.create_index([
            ("challenge", "text"), ("experience", "text"), 
            ("solution", "text"), ("generated_story", "text")
        ])
        await mongodb.database.approved_stories.create_index([("created_at", -1)])
        
        # Add indexes for rejected stories collection
        await mongodb.database.rejected_stories.create_index([("user_id", 1), ("created_at", -1)])
        await mongodb.database.rejected_stories.create_index([("status", 1), ("created_at", 1)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Could not create indexes: {e}")

async def check_database_health() -> bool:
    """Check database connection health"""
    try:
        if mongodb.client is None:
            return False
        await mongodb.client.admin.command('ping')
        return True
    except Exception:
        return False