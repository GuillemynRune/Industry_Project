"""
MongoDB database connection and models
Handles all database operations for postnatal stories
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson import ObjectId
import asyncio

logger = logging.getLogger(__name__)

# Get MongoDB URI from environment
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "postnatal_stories"

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

# Initialize MongoDB connection
mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable not set")
            
        mongodb.client = AsyncIOMotorClient(MONGODB_URI)
        mongodb.database = mongodb.client[DATABASE_NAME]
        
        # Test the connection
        await mongodb.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully!")
        
        # Create indexes
        await create_indexes()
        
        return True
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        return False

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes for better performance"""
    try:
        # Index for text search on stories
        await mongodb.database.recovery_stories.create_index([
            ("challenge", "text"),
            ("experience", "text"), 
            ("solution", "text"),
            ("generated_story", "text")
        ])
        
        # Index for timestamp sorting
        await mongodb.database.recovery_stories.create_index([("created_at", -1)])
        
        # Index for author name
        await mongodb.database.recovery_stories.create_index([("author_name", 1)])
        
        # Index for symptoms collection
        await mongodb.database.symptom_extractions.create_index([("created_at", -1)])
        await mongodb.database.symptom_extractions.create_index([("symptoms_identified", 1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Could not create indexes: {e}")

class StoryDatabase:
    """Database operations for recovery stories"""
    
    @staticmethod
    async def save_recovery_story(
        author_name: str,
        challenge: str,
        experience: str,
        solution: str,
        advice: str,
        generated_story: str,
        model_used: str,
        key_symptoms: List[str] = None  # Add this line
    ) -> Dict:
        """Save a recovery story to the database"""
        
        try:
            story_doc = {
                "author_name": author_name,
                "challenge": challenge,
                "experience": experience,
                "solution": solution,
                "advice": advice,
                "generated_story": generated_story,
                "model_used": model_used,
                "key_symptoms": key_symptoms or [],  # Add this line
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",
                "word_count": len(generated_story.split()),
                "character_count": len(generated_story)
            }
            
            result = await mongodb.database.recovery_stories.insert_one(story_doc)
            
            logger.info(f"Saved recovery story with ID: {result.inserted_id}")
            
            return {
                "success": True,
                "story_id": str(result.inserted_id),
                "message": "Recovery story saved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error saving recovery story: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save recovery story"
            }
    
    @staticmethod
    async def get_recovery_stories(limit: int = 20, skip: int = 0) -> List[Dict]:
        """Get recovery stories from database"""
        
        try:
            cursor = mongodb.database.recovery_stories.find(
                {"status": "active"}
            ).sort("created_at", -1).limit(limit).skip(skip)
            
            stories = await cursor.to_list(length=None)
            
            # Convert ObjectId to string and format dates
            for story in stories:
                story["_id"] = str(story["_id"])
                story["created_at"] = story["created_at"].isoformat()
                story["updated_at"] = story["updated_at"].isoformat()
            
            logger.info(f"Retrieved {len(stories)} recovery stories")
            return stories
            
        except Exception as e:
            logger.error(f"Error retrieving recovery stories: {e}")
            return []
    
    @staticmethod
    async def search_recovery_stories(query: str, limit: int = 10) -> List[Dict]:
        """Search recovery stories by text"""
        
        try:
            # Use MongoDB text search
            cursor = mongodb.database.recovery_stories.find(
                {
                    "$text": {"$search": query},
                    "status": "active"
                },
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            stories = await cursor.to_list(length=None)
            
            # Convert ObjectId to string and format dates
            for story in stories:
                story["_id"] = str(story["_id"])
                story["created_at"] = story["created_at"].isoformat()
                story["updated_at"] = story["updated_at"].isoformat()
            
            logger.info(f"Found {len(stories)} stories matching query: {query}")
            return stories
            
        except Exception as e:
            logger.error(f"Error searching recovery stories: {e}")
            return []
    
    @staticmethod
    async def get_story_by_id(story_id: str) -> Optional[Dict]:
        """Get a specific recovery story by ID"""
        
        try:
            story = await mongodb.database.recovery_stories.find_one(
                {"_id": ObjectId(story_id), "status": "active"}
            )
            
            if story:
                story["_id"] = str(story["_id"])
                story["created_at"] = story["created_at"].isoformat()
                story["updated_at"] = story["updated_at"].isoformat()
            
            return story
            
        except Exception as e:
            logger.error(f"Error retrieving story {story_id}: {e}")
            return None
    
    @staticmethod
    async def get_database_stats() -> Dict:
        """Get database statistics"""
        
        try:
            total_stories = await mongodb.database.recovery_stories.count_documents({"status": "active"})
            total_symptoms = await mongodb.database.symptom_extractions.count_documents({})
            
            # Get recent activity (last 7 days)
            week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            recent_stories = await mongodb.database.recovery_stories.count_documents({
                "created_at": {"$gte": week_ago},
                "status": "active"
            })
            
            return {
                "total_stories": total_stories,
                "total_symptom_extractions": total_symptoms,
                "stories_this_week": recent_stories,
                "database_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {
                "total_stories": 0,
                "total_symptom_extractions": 0,
                "stories_this_week": 0,
                "database_connected": False,
                "error": str(e)
            }

class SymptomDatabase:
    """Database operations for symptom extractions"""
    
    @staticmethod
    async def save_symptom_extraction(
        experience: str,
        feelings: str,
        symptoms_identified: List[str],
        severity_indicators: List[str],
        categories_affected: List[str],
        key_concerns: List[str],
        extraction_method: str,
        insights: Dict
    ) -> Dict:
        """Save symptom extraction results to database"""
        
        try:
            symptom_doc = {
                "experience": experience,
                "feelings": feelings,
                "symptoms_identified": symptoms_identified,
                "severity_indicators": severity_indicators,
                "categories_affected": categories_affected,
                "key_concerns": key_concerns,
                "extraction_method": extraction_method,
                "insights": insights,
                "created_at": datetime.utcnow(),
                "symptom_count": len(symptoms_identified),
                "risk_level": insights.get("risk_level", "unknown")
            }
            
            result = await mongodb.database.symptom_extractions.insert_one(symptom_doc)
            
            logger.info(f"Saved symptom extraction with ID: {result.inserted_id}")
            
            return {
                "success": True,
                "extraction_id": str(result.inserted_id),
                "message": "Symptom extraction saved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error saving symptom extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save symptom extraction"
            }
    
    @staticmethod
    async def get_symptom_patterns() -> Dict:
        """Get patterns from symptom extractions for insights"""
        
        try:
            # Aggregate common symptoms
            pipeline = [
                {"$unwind": "$symptoms_identified"},
                {"$group": {
                    "_id": "$symptoms_identified",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            common_symptoms = await mongodb.database.symptom_extractions.aggregate(pipeline).to_list(length=None)
            
            # Get risk level distribution
            risk_pipeline = [
                {"$group": {
                    "_id": "$risk_level",
                    "count": {"$sum": 1}
                }}
            ]
            
            risk_distribution = await mongodb.database.symptom_extractions.aggregate(risk_pipeline).to_list(length=None)
            
            return {
                "common_symptoms": common_symptoms,
                "risk_distribution": risk_distribution,
                "analysis_available": True
            }
            
        except Exception as e:
            logger.error(f"Error getting symptom patterns: {e}")
            return {
                "common_symptoms": [],
                "risk_distribution": [],
                "analysis_available": False,
                "error": str(e)
            }

# Database health check
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