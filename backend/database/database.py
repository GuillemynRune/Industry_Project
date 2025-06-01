"""
MongoDB database connection and models
Handles all database operations for postnatal stories
"""

import os
import logging
import re
from datetime import datetime, timedelta
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
        
        # Indexes for user management
        await mongodb.database.users.create_index([("email", 1)], unique=True)
        await mongodb.database.users.create_index([("created_at", -1)])
        
        # Indexes for moderation
        await mongodb.database.pending_stories.create_index([("status", 1), ("created_at", 1)])
        await mongodb.database.pending_stories.create_index([("risk_level", 1)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Could not create indexes: {e}")
    
    @staticmethod
    async def get_recovery_stories(limit: int = 20, skip: int = 0) -> List[Dict]:
        """Get recovery stories from database"""
        
        try:
            cursor = mongodb.database.recovery_stories.find(
                {"status": {"$in": ["active", "approved"]}}  # Support both old and new status values
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
                    "status": {"$in": ["active", "approved"]}
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
                {"_id": ObjectId(story_id), "status": {"$in": ["active", "approved"]}}
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
            total_stories = await mongodb.database.recovery_stories.count_documents({
                "status": {"$in": ["active", "approved"]}
            })
            total_symptoms = await mongodb.database.symptom_extractions.count_documents({})
            
            # Get recent activity (last 7 days)
            week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            recent_stories = await mongodb.database.recovery_stories.count_documents({
                "created_at": {"$gte": week_ago},
                "status": {"$in": ["active", "approved"]}
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

class UserDatabase:
    """Database operations for user management"""
    
    @staticmethod
    async def create_user(email: str, password_hash: str, display_name: str = None) -> Dict:
        """Create a new user account"""
        try:
            # Check if user already exists
            existing_user = await mongodb.database.users.find_one({"email": email.lower()})
            if existing_user:
                return {"success": False, "message": "User already exists"}
            
            user_doc = {
                "email": email.lower(),
                "password_hash": password_hash,
                "display_name": display_name or "Anonymous",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "role": "user",
                "email_verified": False,
                "stories_shared": 0,
                "last_login": None,
                "agreed_to_terms_at": datetime.utcnow(),
                "age_verified": True
            }
            
            result = await mongodb.database.users.insert_one(user_doc)
            logger.info(f"Created user account: {email}")
            
            return {
                "success": True,
                "user_id": str(result.inserted_id),
                "message": "User created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {"success": False, "message": "Failed to create user"}
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            user = await mongodb.database.users.find_one({"email": email.lower()})
            if user:
                user["id"] = str(user["_id"])
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    async def update_last_login(email: str):
        """Update user's last login time"""
        try:
            await mongodb.database.users.update_one(
                {"email": email.lower()},
                {"$set": {"last_login": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating last login: {e}")

class ModerationDatabase:
    """Database operations for content moderation"""
    
    @staticmethod
    async def submit_story_for_review(
        user_id: str,
        author_name: str,
        challenge: str,
        experience: str,
        solution: str,
        advice: str,
        generated_story: str,
        model_used: str,
        key_symptoms: List[str] = None
    ) -> Dict:
        """Submit story for moderation review"""
        
        try:
            # Auto-flag potentially concerning content
            risk_level = await ModerationDatabase._assess_content_risk(
                experience, advice, generated_story
            )
            
            story_doc = {
                "user_id": user_id,
                "author_name": author_name,
                "challenge": challenge,
                "experience": experience,
                "solution": solution,
                "advice": advice,
                "generated_story": generated_story,
                "model_used": model_used,
                "key_symptoms": key_symptoms or [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "pending_review",
                "risk_level": risk_level,
                "moderated_by": None,
                "moderated_at": None,
                "moderation_notes": "",
                "word_count": len(generated_story.split()),
                "character_count": len(generated_story),
                "flagged_keywords": await ModerationDatabase._check_keywords(experience + " " + advice)
            }
            
            result = await mongodb.database.pending_stories.insert_one(story_doc)
            logger.info(f"Story submitted for review with ID: {result.inserted_id}")
            
            return {
                "success": True,
                "story_id": str(result.inserted_id),
                "status": "submitted_for_review",
                "estimated_review_time": "24-48 hours",
                "message": "Your story has been submitted and will be reviewed before publication"
            }
            
        except Exception as e:
            logger.error(f"Error submitting story for review: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit story for review"
            }
    
    @staticmethod
    async def _assess_content_risk(experience: str, advice: str, generated_story: str) -> str:
        """Assess risk level of content"""
        combined_text = f"{experience} {advice} {generated_story}".lower()
        
        # High-risk keywords (require immediate review)
        high_risk_keywords = [
            "suicide", "kill myself", "end it all", "not worth living", 
            "hurt myself", "self harm", "overdose", "die", "death wish"
        ]
        
        # Medium-risk indicators
        medium_risk_keywords = [
            "hopeless", "can't cope", "giving up", "too much", "breaking down",
            "can't handle", "losing control", "scared", "terrified", "panic"
        ]
        
        # Check for high-risk content
        for keyword in high_risk_keywords:
            if keyword in combined_text:
                return "high"
        
        # Check for medium-risk content
        risk_count = sum(1 for keyword in medium_risk_keywords if keyword in combined_text)
        if risk_count >= 3:
            return "medium"
        elif risk_count >= 1:
            return "low"
        
        return "minimal"
    
    @staticmethod
    async def _check_keywords(text: str) -> List[str]:
        """Check for flagged keywords in content"""
        flagged = []
        text_lower = text.lower()
        
        concern_keywords = [
            "suicide", "self harm", "hurt myself", "kill myself", "hopeless",
            "can't cope", "giving up", "breaking down", "losing control"
        ]
        
        for keyword in concern_keywords:
            if keyword in text_lower:
                flagged.append(keyword)
        
        return flagged
    
    @staticmethod
    async def get_pending_stories(limit: int = 20) -> List[Dict]:
        """Get stories pending moderation"""
        try:
            cursor = mongodb.database.pending_stories.find(
                {"status": "pending_review"}
            ).sort("created_at", 1).limit(limit)
            
            stories = await cursor.to_list(length=None)
            
            for story in stories:
                story["_id"] = str(story["_id"])
                story["created_at"] = story["created_at"].isoformat()
                
            return stories
            
        except Exception as e:
            logger.error(f"Error getting pending stories: {e}")
            return []
    
    @staticmethod
    async def approve_story(story_id: str, moderator_id: str, notes: str = "") -> Dict:
        """Approve a story and move it to published stories"""
        try:
            # Get the pending story
            pending_story = await mongodb.database.pending_stories.find_one(
                {"_id": ObjectId(story_id)}
            )
            
            if not pending_story:
                return {"success": False, "message": "Story not found"}
            
            # Move to approved stories collection
            approved_story = pending_story.copy()
            approved_story["status"] = "approved"
            approved_story["moderated_by"] = moderator_id
            approved_story["moderated_at"] = datetime.utcnow()
            approved_story["moderation_notes"] = notes
            del approved_story["_id"]
            
            # Insert into recovery_stories collection
            result = await mongodb.database.recovery_stories.insert_one(approved_story)
            
            # Remove from pending
            await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
            
            # Update user's story count
            await mongodb.database.users.update_one(
                {"_id": ObjectId(pending_story["user_id"])},
                {"$inc": {"stories_shared": 1}}
            )
            
            logger.info(f"Story {story_id} approved and published")
            
            return {
                "success": True,
                "published_story_id": str(result.inserted_id),
                "message": "Story approved and published"
            }
            
        except Exception as e:
            logger.error(f"Error approving story: {e}")
            return {"success": False, "message": "Failed to approve story"}

class CrisisSupport:
    """Crisis support and resources"""
    
    @staticmethod
    def get_crisis_resources() -> Dict:
        """Get crisis support resources"""
        return {
            "immediate_help": {
                "suicide_lifeline": {
                    "number": "988",
                    "description": "Suicide & Crisis Lifeline (US)",
                    "available": "24/7"
                },
                "postpartum_support": {
                    "number": "1-800-944-4773",
                    "description": "Postpartum Support International Helpline",
                    "available": "24/7"
                },
                "crisis_text": {
                    "number": "Text HOME to 741741",
                    "description": "Crisis Text Line",
                    "available": "24/7"
                }
            },
            "online_resources": [
                {
                    "name": "Postpartum Support International",
                    "url": "https://postpartum.net",
                    "description": "Resources and support for perinatal mental health"
                },
                {
                    "name": "SAMHSA Treatment Locator",
                    "url": "https://findtreatment.samhsa.gov",
                    "description": "Find mental health treatment in your area"
                }
            ],
            "warning_signs": [
                "Thoughts of harming yourself or your baby",
                "Feeling like you might hurt yourself",
                "Thoughts of suicide or death",
                "Severe anxiety or panic attacks",
                "Feeling completely overwhelmed and unable to cope"
            ]
        }
    
    @staticmethod
    async def log_crisis_interaction(user_id: str = None, interaction_type: str = "resource_view"):
        """Log when someone accesses crisis resources"""
        try:
            await mongodb.database.crisis_interactions.insert_one({
                "user_id": user_id,
                "interaction_type": interaction_type,
                "timestamp": datetime.utcnow(),
                "ip_hash": None
            })
        except Exception as e:
            logger.error(f"Error logging crisis interaction: {e}")

class ContentFilter:
    """Content filtering and safety checks"""
    
    CRISIS_KEYWORDS = [
        "suicide", "kill myself", "end it all", "not worth living",
        "hurt myself", "self harm", "overdose", "want to die"
    ]
    
    URGENT_KEYWORDS = [
        "can't cope", "breaking down", "losing control", "hopeless",
        "give up", "can't handle", "too much", "overwhelmed"
    ]
    
    @staticmethod
    def requires_immediate_attention(text: str) -> bool:
        """Check if content requires immediate crisis intervention"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ContentFilter.CRISIS_KEYWORDS)
    
    @staticmethod
    def get_risk_assessment(text: str) -> Dict:
        """Assess risk level of user input"""
        text_lower = text.lower()
        
        crisis_count = sum(1 for keyword in ContentFilter.CRISIS_KEYWORDS if keyword in text_lower)
        urgent_count = sum(1 for keyword in ContentFilter.URGENT_KEYWORDS if keyword in text_lower)
        
        if crisis_count > 0:
            return {
                "risk_level": "critical",
                "requires_intervention": True,
                "recommended_action": "immediate_crisis_support"
            }
        elif urgent_count >= 3:
            return {
                "risk_level": "high", 
                "requires_intervention": True,
                "recommended_action": "professional_resources"
            }
        elif urgent_count >= 1:
            return {
                "risk_level": "moderate",
                "requires_intervention": False,
                "recommended_action": "support_resources"
            }
        else:
            return {
                "risk_level": "low",
                "requires_intervention": False,
                "recommended_action": "community_support"
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