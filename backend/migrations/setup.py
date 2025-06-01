from ..database import mongodb
from ..database.connection import create_indexes
import logging

logger = logging.getLogger(__name__)


async def ensure_production_ready():
    """Ensure database is production ready"""
    try:
        # Check if collections exist, create if not
        collections = await mongodb.database.list_collection_names()
        
        required_collections = [
            "users", "recovery_stories", "pending_stories", 
            "approved_stories", "symptom_extractions"
        ]
        
        for collection in required_collections:
            if collection not in collections:
                await mongodb.database.create_collection(collection)
                logger.info(f"Created collection: {collection}")
        
        # Ensure indexes exist (your create_indexes function already does this)
        await create_indexes()
        
        logger.info("Database migration completed")
        return True
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False