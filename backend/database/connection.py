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
    try:
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable not set")
            
        mongodb.client = AsyncIOMotorClient(MONGODB_URI)
        mongodb.database = mongodb.client[DATABASE_NAME]
        
        await mongodb.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully!")
        
        await create_indexes()
        return True
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes"""
    try:        
        # User indexes
        await mongodb.database.users.create_index([("email", 1)], unique=True)
        
        # Moderation indexes
        await mongodb.database.pending_stories.create_index([("status", 1), ("created_at", 1)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Could not create indexes: {e}")

async def check_database_health() -> bool:
    """Check if database connection is healthy"""
    try:
        if mongodb.client is None:
            return False
        await mongodb.client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False