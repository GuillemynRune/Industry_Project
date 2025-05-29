import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from database.connection import mongodb

logger = logging.getLogger(__name__)

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

class ContentFilter:
    """Content filtering and safety utilities"""
    
    CRISIS_KEYWORDS = [
        "suicide", "kill myself", "end it all", "can't go on", "no hope",
        "want to die", "ending my life", "self harm", "hurt myself"
    ]
    
    INAPPROPRIATE_KEYWORDS = [
        "explicit sexual content", "violence", "hate speech", "spam"
    ]
    
    @staticmethod
    def check_for_crisis_content(text: str) -> Dict[str, Any]:
        """Check if content contains crisis indicators"""
        text_lower = text.lower()
        crisis_indicators = []
        
        for keyword in ContentFilter.CRISIS_KEYWORDS:
            if keyword in text_lower:
                crisis_indicators.append(keyword)
        
        return {
            "has_crisis_content": len(crisis_indicators) > 0,
            "crisis_indicators": crisis_indicators,
            "severity": "high" if len(crisis_indicators) > 2 else "medium" if len(crisis_indicators) > 0 else "low"
        }
    
    @staticmethod
    def check_content_appropriateness(text: str) -> Dict[str, Any]:
        """Check if content is appropriate"""
        text_lower = text.lower()
        inappropriate_flags = []
        
        for keyword in ContentFilter.INAPPROPRIATE_KEYWORDS:
            if keyword in text_lower:
                inappropriate_flags.append(keyword)
        
        return {
            "is_appropriate": len(inappropriate_flags) == 0,
            "flags": inappropriate_flags,
            "requires_moderation": len(inappropriate_flags) > 0
        }
    
    @staticmethod
    def get_risk_assessment(text: str) -> Dict[str, Any]:
        """Assess risk level of content for crisis intervention"""
        crisis_check = ContentFilter.check_for_crisis_content(text)
        
        return {
            "requires_intervention": crisis_check["has_crisis_content"] and crisis_check["severity"] in ["high", "medium"],
            "crisis_indicators": crisis_check["crisis_indicators"],
            "severity": crisis_check["severity"],
            "recommendations": ContentFilter._get_intervention_recommendations(crisis_check["severity"])
        }
    
    @staticmethod
    def _get_intervention_recommendations(severity: str) -> List[str]:
        """Get intervention recommendations based on severity"""
        if severity == "high":
            return ["immediate_crisis_support", "emergency_services", "continuous_monitoring"]
        elif severity == "medium":
            return ["crisis_resources", "professional_support", "follow_up"]
        else:
            return ["general_support", "resource_awareness"]
    
    @staticmethod
    async def log_content_flag(content_type: str, content_id: str, flags: List[str], user_id: Optional[str] = None) -> bool:
        """Log flagged content"""
        try:
            flag_doc = {
                "content_type": content_type,
                "content_id": content_id,
                "flags": flags,
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }
            
            await mongodb.database.content_flags.insert_one(flag_doc)
            return True
            
        except Exception as e:
            logger.error(f"Error logging content flag: {e}")
            return False