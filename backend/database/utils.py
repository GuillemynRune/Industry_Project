import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from .connection import mongodb

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
            await mongodb.database.crisis_interactions.insert_one({
                "interaction_type": interaction_type,
                "user_id": user_id,
                "created_at": datetime.utcnow()
            })
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
    
    @staticmethod
    def get_risk_assessment(text: str) -> Dict[str, Any]:
        """Assess risk level for crisis intervention"""
        text_lower = text.lower()
        crisis_indicators = [kw for kw in ContentFilter.CRISIS_KEYWORDS if kw in text_lower]
        
        severity = "high" if len(crisis_indicators) > 2 else "medium" if crisis_indicators else "low"
        
        return {
            "requires_intervention": len(crisis_indicators) > 0 and severity in ["high", "medium"],
            "crisis_indicators": crisis_indicators,
            "severity": severity
        }