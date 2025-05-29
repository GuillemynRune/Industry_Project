import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
from database.connection import mongodb

logger = logging.getLogger(__name__)

class SymptomDatabase:
    """Symptom extraction database operations"""
    
    @staticmethod
    async def save_symptom_extraction(
        experience: str,
        feelings: str,
        symptoms_identified: List[str],
        severity_indicators: List[str],
        categories_affected: List[str],
        key_concerns: List[str],
        extraction_method: str,
        insights: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save symptom extraction results"""
        try:
            extraction_doc = {
                "experience": experience,
                "feelings": feelings,
                "symptoms_identified": symptoms_identified,
                "severity_indicators": severity_indicators,
                "categories_affected": categories_affected,
                "key_concerns": key_concerns,
                "extraction_method": extraction_method,
                "insights": insights,
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }
            
            result = await mongodb.database.symptom_extractions.insert_one(extraction_doc)
            
            return {
                "success": True,
                "message": "Symptom extraction saved successfully",
                "extraction_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Error saving symptom extraction: {e}")
            return {"success": False, "message": "Failed to save extraction"}
    
    @staticmethod
    async def get_symptom_patterns() -> Dict[str, Any]:
        """Get common symptom patterns from database"""
        try:
            # Aggregate most common symptoms
            pipeline = [
                {"$unwind": "$symptoms_identified"},
                {"$group": {
                    "_id": "$symptoms_identified",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            common_symptoms = []
            async for symptom in mongodb.database.symptom_extractions.aggregate(pipeline):
                common_symptoms.append({
                    "symptom": symptom["_id"],
                    "frequency": symptom["count"]
                })
            
            # Aggregate severity patterns
            severity_pipeline = [
                {"$unwind": "$severity_indicators"},
                {"$group": {
                    "_id": "$severity_indicators",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            severity_patterns = []
            async for severity in mongodb.database.symptom_extractions.aggregate(severity_pipeline):
                severity_patterns.append({
                    "severity": severity["_id"],
                    "frequency": severity["count"]
                })
            
            total_extractions = await mongodb.database.symptom_extractions.count_documents({})
            
            return {
                "total_extractions": total_extractions,
                "common_symptoms": common_symptoms,
                "severity_patterns": severity_patterns
            }
            
        except Exception as e:
            logger.error(f"Error getting symptom patterns: {e}")
            return {}

class CrisisSupport:
    """Crisis support utilities"""
    
    @staticmethod
    def get_crisis_resources() -> List[Dict[str, str]]:
        """Get crisis support resources"""
        return [
            {
                "name": "National Suicide Prevention Lifeline",
                "phone": "988",
                "description": "24/7 free and confidential support"
            },
            {
                "name": "Crisis Text Line",
                "phone": "Text HOME to 741741",
                "description": "24/7 crisis support via text"
            },
            {
                "name": "Postpartum International Helpline",
                "phone": "1-944-4-PSI-HELP",
                "description": "Specialized postpartum support"
            },
            {
                "name": "Emergency Services",
                "phone": "911",
                "description": "Immediate emergency assistance"
            }
        ]
    
    @staticmethod
    async def log_crisis_interaction(interaction_type: str, user_id: Optional[str] = None) -> bool:
        """Log crisis support interaction"""
        try:
            interaction_doc = {
                "interaction_type": interaction_type,
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }
            
            await mongodb.database.crisis_interactions.insert_one(interaction_doc)
            return True
            
        except Exception as e:
            logger.error(f"Error logging crisis interaction: {e}")
            return False