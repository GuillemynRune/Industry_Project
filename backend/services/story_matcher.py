"""
Story matching service using sentence transformers for semantic similarity - WITH DEBUGGING
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional
import os
import logging
import traceback

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
            
            # Test the model with a simple sentence
            test_text = "This is a test sentence"
            test_embedding = self.model.encode(test_text)
            logger.info(f"✓ Model test successful - embedding shape: {test_embedding.shape}, type: {type(test_embedding)}")
            
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.info("Falling back to default model")
            try:
                self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2', cache_folder=cache_dir)
                logger.info("✓ Fallback model loaded successfully")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback model also failed: {fallback_error}")
                self.model = None

    def create_story_embedding_text(self, story_doc: Dict) -> str:
        """Create text for embedding from MongoDB story structure"""
        try:
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
            
            result = " | ".join(text_parts)
            logger.info(f"Created embedding text with length: {len(result)}")
            logger.debug(f"Embedding text preview: {result[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error creating embedding text: {e}")
            logger.error(f"Story doc keys: {list(story_doc.keys()) if story_doc else 'None'}")
            return "Error creating embedding text"

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text with detailed logging"""
        try:
            if not self.model:
                logger.error("Model not loaded, cannot generate embedding")
                return []
            
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return []
            
            logger.info(f"Generating embedding for text of length {len(text)}")
            logger.debug(f"Text preview: {text[:100]}...")
            
            # Generate embedding
            embedding = self.model.encode(text)
            
            if embedding is None:
                logger.error("Model returned None for embedding")
                return []
            
            # Convert to list if it's a numpy array
            if isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
                logger.info(f"✓ Generated embedding: shape={embedding.shape}, type={type(embedding)}, list_length={len(embedding_list)}")
                return embedding_list
            else:
                logger.warning(f"Unexpected embedding type: {type(embedding)}")
                return []
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
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
            if not self.model:
                logger.error("Model not loaded, cannot find similar stories")
                return []
            
            logger.info(f"Finding similar stories for input text of length {len(input_text)}")
            
            input_embedding = self.model.encode(input_text)
            
            if input_embedding is None:
                logger.error("Failed to generate input embedding")
                return []
            
            logger.info(f"Input embedding generated: shape={input_embedding.shape}")
            
            stories_cursor = stories_collection.find({
                "embedding": {"$exists": True, "$ne": None},
                "status": "approved"
            })
            
            similarities = []
            story_count = 0
            
            async for story in stories_cursor:
                story_count += 1
                try:
                    if not story.get("embedding"):
                        logger.debug(f"Story {story.get('_id')} has no embedding")
                        continue
                        
                    story_embedding = np.array(story["embedding"])
                    
                    if story_embedding.size == 0:
                        logger.debug(f"Story {story.get('_id')} has empty embedding")
                        continue
                    
                    similarity = cosine_similarity([input_embedding], [story_embedding])[0][0]
                    
                    if similarity >= min_similarity:
                        similarities.append({
                            "story": story,
                            "similarity": float(similarity)
                        })
                        
                except Exception as e:
                    logger.warning(f"Error processing story {story.get('_id')}: {e}")
                    continue
            
            logger.info(f"Processed {story_count} stories, found {len(similarities)} similar ones")
            
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
            
            logger.info(f"Returning {len(results)} similar stories")
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    def _explain_match(self, input_text: str, story: Dict) -> str:
        """Generate explanation for why stories match"""
        try:
            input_themes = set(self._extract_key_themes(input_text))
            story_text = self.create_story_embedding_text(story)
            story_themes = set(self._extract_key_themes(story_text))
            
            common_themes = input_themes.intersection(story_themes)
            
            if common_themes:
                theme_str = ', '.join(common_themes)
                return f"Similar experiences with: {theme_str}"
            return "Similar emotional journey and experiences"
        except Exception as e:
            logger.warning(f"Error explaining match: {e}")
            return "Similar experiences"

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