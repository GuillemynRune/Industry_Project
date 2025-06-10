"""
Story matching service using sentence transformers for semantic similarity
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

class StoryMatcher:
    def __init__(self, model_name='all-distilroberta-v1', cache_dir='./ai_models'):
        """Initialize the story matching system"""
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"Loading model '{model_name}' to {os.path.abspath(cache_dir)}")
        
        try:
            self.model = SentenceTransformer(
                model_name, 
                cache_folder=cache_dir,
                trust_remote_code=True
            )
            logger.info("✓ Model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            logger.info("Falling back to default model")
            self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2', cache_folder=cache_dir)

    def create_story_embedding_text(self, story_doc: Dict) -> str:
        """Create text for embedding from MongoDB story structure"""
        text_parts = []
        
        fields = [
            ("Challenge", "challenge"),
            ("Experience", "experience"), 
            ("Solution", "solution"),
            ("Advice", "advice")
        ]
        
        for label, field in fields:
            if story_doc.get(field):
                text_parts.append(f"{label}: {story_doc[field]}")
        
        # Add symptoms
        if story_doc.get("key_symptoms"):
            symptoms = ", ".join(story_doc["key_symptoms"])
            text_parts.append(f"Symptoms: {symptoms}")
        
        # Add truncated story
        if story_doc.get("generated_story"):
            story_text = story_doc["generated_story"]
            if len(story_text) > 500:
                story_text = story_text[:500] + "..."
            text_parts.append(f"Story: {story_text}")
        
        return " | ".join(text_parts)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def find_similar_stories_with_embeddings(
        self, 
        input_text: str, 
        stories_collection, 
        top_k: int = 9, 
        min_similarity: float = 0.1
    ) -> List[Dict]:
        """Find similar stories using pre-computed embeddings"""
        try:
            input_embedding = self.model.encode(input_text)
            
            stories_cursor = stories_collection.find({
                "embedding": {"$exists": True},
                "status": "approved"
            })
            
            similarities = []
            async for story in stories_cursor:
                try:
                    story_embedding = np.array(story["embedding"])
                    similarity = cosine_similarity([input_embedding], [story_embedding])[0][0]
                    
                    if similarity >= min_similarity:
                        similarities.append({
                            "story": story,
                            "similarity": float(similarity)
                        })
                except Exception as e:
                    logger.warning(f"Error processing story {story.get('_id')}: {e}")
                    continue
            
            # Sort by similarity and format results
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            results = []
            for item in similarities[:top_k]:
                story = item["story"].copy()
                story.pop("embedding", None)  # Remove large embedding
                
                if "_id" in story:
                    story["_id"] = str(story["_id"])
                
                results.append({
                    "story": story,
                    "similarity": item["similarity"],
                    "match_explanation": self._explain_match(input_text, story)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    def _explain_match(self, input_text: str, story: Dict) -> str:
        """Generate explanation for why stories match"""
        input_themes = set(self._extract_key_themes(input_text))
        story_text = self.create_story_embedding_text(story)
        story_themes = set(self._extract_key_themes(story_text))
        
        common_themes = input_themes.intersection(story_themes)
        
        if common_themes:
            theme_str = ', '.join(common_themes)
            return f"Similar experiences with: {theme_str}"
        return "Similar emotional journey and experiences"

    def _extract_key_themes(self, text: str) -> List[str]:
        """Extract key themes for postnatal stories"""
        theme_keywords = {
            'depression': ['depression', 'depressed', 'sad', 'hopeless', 'worthless', 'empty', 'dark'],
            'anxiety': ['anxiety', 'anxious', 'worried', 'panic', 'overwhelmed', 'scared', 'fear'],
            'isolation': ['lonely', 'alone', 'isolated', 'no one', 'support', 'friends'],
            'sleep': ['sleep', 'tired', 'exhausted', 'insomnia', 'sleepless', 'fatigue'],
            'feeding': ['breastfeeding', 'feeding', 'bottle', 'latch', 'milk', 'nutrition'],
            'bonding': ['bond', 'bonding', 'connection', 'attachment', 'love', 'feelings'],
            'identity': ['identity', 'myself', 'who am i', 'lost', 'changed', 'person'],
            'relationship': ['partner', 'husband', 'relationship', 'marriage', 'spouse'],
            'support': ['help', 'support', 'therapy', 'counselor', 'treatment', 'medication'],
            'recovery': ['better', 'healing', 'recovery', 'improvement', 'hope', 'progress'],
            'guilt': ['guilt', 'shame', 'failure', 'bad mother', 'not enough'],
            'baby': ['baby', 'newborn', 'infant', 'child', 'crying', 'care']
        }
        
        text_lower = text.lower()
        themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                themes.append(theme)
        
        return themes

# Global instance
story_matcher = StoryMatcher()