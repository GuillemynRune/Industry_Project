# backend/database/utils.py
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
        """Log crisis support interaction - DISABLED"""
        try:
            # Database logging disabled - just log to console
            logger.info(f"Crisis interaction: {interaction_type} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error logging crisis interaction: {e}")
            return False

# Removed ContentFilter class entirely