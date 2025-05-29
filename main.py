# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import uvicorn
import logging
import os
import secrets

# Import our modular services
from services.story_service import create_recovery_story_prompt
from services.symptom_service import extract_symptoms, get_symptom_insights
from services.ollama_client import validate_ollama_connection, test_model_connection, MODELS, query_ollama_model

# Import database functionality
from database import connect_to_mongo, close_mongo_connection, StoryDatabase, SymptomDatabase, UserDatabase, ModerationDatabase, CrisisSupport, ContentFilter

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(
    title="Postnatal Stories API",
    description="API for transforming recovery stories and connecting parents (using Ollama)",
    version="2.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Pydantic models
class StoryRequest(BaseModel):
    author_name: Optional[str] = "Anonymous"
    challenge: str
    experience: str
    solution: str
    advice: Optional[str] = ""

class StoryResponse(BaseModel):
    success: bool
    story: Optional[str] = None
    author_name: str
    message: str
    model_used: Optional[str] = None
    story_id: Optional[str] = None

class SymptomRequest(BaseModel):
    experience: str
    feelings: str

class SymptomResponse(BaseModel):
    success: bool
    symptoms_identified: List[str]
    severity_indicators: List[str]
    categories_affected: List[str]
    key_concerns: List[str]
    extraction_method: str
    insights: Dict
    message: str

class SearchRequest(BaseModel):
    query: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    agrees_to_terms: bool = True
    age_verified: bool = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    created_at: datetime
    is_active: bool
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await UserDatabase.get_user_by_email(user_email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Database connection events
@app.on_event("startup")
async def startup_event():
    try:
        await connect_to_mongo()
        logger.info("Database connected successfully on startup")
    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await close_mongo_connection()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")

async def generate_recovery_story(challenge: str, experience: str, solution: str, advice: str = "", author_name: str = "Anonymous") -> dict:
    """Generate a recovery story using Ollama and save to database"""
    
    try:
        prompt = create_recovery_story_prompt(challenge, experience, solution, advice)
        
        story = None
        model_used = None
        
        for model_name in MODELS:
            try:
                logger.info(f"Trying model: {model_name}")
                
                generated_text = query_ollama_model(model_name, prompt, max_tokens=150)
                
                if generated_text and len(generated_text.strip()) > 100:
                    story = generated_text.strip()
                    model_used = model_name
                    break
                        
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}")
                continue
        
        if not story or len(story.strip()) < 100:
            story = create_fallback_recovery_story(challenge, experience, solution, advice)
            model_used = "fallback"
            logger.info("Used fallback recovery story")

        try:
            symptom_data = extract_symptoms(
                experience=f"{challenge}. {experience}",
                feelings=advice
            )
            key_symptoms = symptom_data.get("symptoms_identified", [])[:3]
            logger.info(f"Extracted key symptoms: {key_symptoms}")
        except Exception as e:
            logger.warning(f"Symptom extraction failed: {e}")
            key_symptoms = []
        
        return {
            "success": True,
            "story": story,
            "author_name": author_name,
            "model_used": model_used,
            "key_symptoms": key_symptoms,
            "message": f"Recovery story created using {model_used}"
        }
        
    except Exception as e:
        logger.error(f"Error generating recovery story: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "story": create_fallback_recovery_story(challenge, experience, solution, advice),
            "author_name": author_name,
            "model_used": "fallback",
            "key_symptoms": []
        }

def create_fallback_recovery_story(challenge: str, experience: str, solution: str, advice: str = "") -> str:
    """Create a recovery story when AI models fail"""
    story = f"Recovery Story: Overcoming {challenge}\n\n"
    story += f"The challenge: {experience[:150]}{'...' if len(experience) > 150 else ''}\n\n"
    story += f"What helped: {solution[:150]}{'...' if len(solution) > 150 else ''}\n\n"
    if advice:
        story += f"Advice to others: {advice[:100]}{'...' if len(advice) > 100 else ''}\n\n"
    story += "Remember: Recovery is possible. Every small step forward matters, and you're not alone in this journey."
    
    return story

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Postnatal Recovery Stories API v2.1 - Using Ollama!",
        "features": [
            "Recovery story transformation (local AI)",
            "Symptom extraction (local AI)", 
            "Support insights",
            "User authentication",
            "Content moderation",
            "Crisis support",
            "MongoDB database storage"
        ],
        "ollama_required": "Make sure Ollama is running with phi4 model"
    }

@app.get("/health")
async def health_check():
    from database import check_database_health
    
    ollama_connected, ollama_info = validate_ollama_connection()
    db_healthy = await check_database_health()
    
    return {
        "status": "healthy" if (ollama_connected and db_healthy) else "degraded",
        "ollama_connected": ollama_connected,
        "ollama_info": ollama_info,
        "database_connected": db_healthy,
        "available_models": len(MODELS),
        "features_enabled": ["recovery_story_generation", "symptom_extraction", "database_storage", "authentication", "moderation"]
    }

# Authentication endpoints
@app.post("/auth/register")
@limiter.limit("3/minute")
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user account"""
    
    if not user_data.age_verified:
        raise HTTPException(status_code=400, detail="You must be 18 or older to use this service")
    
    if not user_data.agrees_to_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms of service")
    
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    try:
        password_hash = get_password_hash(user_data.password)
        
        result = await UserDatabase.create_user(
            email=user_data.email,
            password_hash=password_hash,
            display_name=user_data.display_name
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Account created successfully! You can now log in.",
                "user_id": result["user_id"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create account")

@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
async def login_user(request: Request, user_data: UserLogin):
    """Login user and return access token"""
    
    try:
        user = await UserDatabase.get_user_by_email(user_data.email)
        
        if not user or not verify_password(user_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        if not user.get("is_active", False):
            raise HTTPException(status_code=400, detail="Account is deactivated")
        
        await UserDatabase.update_last_login(user_data.email)
        
        access_token = create_access_token(
            data={"sub": user["email"]},
            expires_delta=timedelta(minutes=60*24*7)
        )
        
        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user.get("display_name", "Anonymous"),
            created_at=user["created_at"],
            is_active=user["is_active"],
            role=user.get("role", "user")
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        display_name=current_user.get("display_name", "Anonymous"),
        created_at=current_user["created_at"],
        is_active=current_user["is_active"],
        role=current_user.get("role", "user")
    )

# Story endpoints
@app.post("/stories/submit")
@limiter.limit("5/hour")
async def submit_story_for_review(
    request: Request,
    story_request: StoryRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Submit a story for moderation review (requires authentication)"""
    
    if not story_request.challenge.strip() or not story_request.experience.strip() or not story_request.solution.strip():
        raise HTTPException(status_code=400, detail="Challenge, experience, and solution cannot be empty")
    
    try:
        combined_text = f"{story_request.experience} {story_request.advice}"
        risk_assessment = ContentFilter.get_risk_assessment(combined_text)
        
        if risk_assessment["requires_intervention"]:
            await CrisisSupport.log_crisis_interaction(
                user_id=current_user["id"],
                interaction_type="crisis_content_detected"
            )
            
            crisis_resources = CrisisSupport.get_crisis_resources()
            return {
                "success": False,
                "requires_immediate_support": True,
                "crisis_resources": crisis_resources,
                "message": "We noticed your message indicates you might be in distress. Please reach out for immediate support."
            }
        
        story_result = await generate_recovery_story(
            challenge=story_request.challenge,
            experience=story_request.experience,
            solution=story_request.solution,
            advice=story_request.advice,
            author_name=story_request.author_name or current_user.get("display_name", "Anonymous")
        )
        
        if not story_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate story")
        
        moderation_result = await ModerationDatabase.submit_story_for_review(
            user_id=current_user["id"],
            author_name=story_request.author_name or current_user.get("display_name", "Anonymous"),
            challenge=story_request.challenge,
            experience=story_request.experience,
            solution=story_request.solution,
            advice=story_request.advice,
            generated_story=story_result["story"],
            model_used=story_result["model_used"],
            key_symptoms=story_result.get("key_symptoms", [])
        )
        
        return {
            "success": True,
            "message": "Your story has been submitted for review and will be published within 24-48 hours.",
            "story_id": moderation_result["story_id"],
            "estimated_review_time": moderation_result["estimated_review_time"],
            "story_preview": story_result["story"][:200] + "..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story submission error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit story")

@app.post("/transform-story", response_model=StoryResponse)
async def transform_recovery_story(request: StoryRequest):
    """Transform recovery experience into inspiring story using Ollama (deprecated - use /stories/submit)"""
    
    if not request.challenge.strip() or not request.experience.strip() or not request.solution.strip():
        raise HTTPException(status_code=400, detail="Challenge, experience, and solution cannot be empty")
    
    try:
        result = await generate_recovery_story(
            challenge=request.challenge,
            experience=request.experience,
            solution=request.solution,
            advice=request.advice,
            author_name=request.author_name
        )
        
        # Save directly without moderation for backward compatibility
        save_result = await StoryDatabase.save_recovery_story(
            author_name=result["author_name"],
            challenge=request.challenge,
            experience=request.experience,
            solution=request.solution,
            advice=request.advice,
            generated_story=result["story"],
            model_used=result["model_used"],
            key_symptoms=result.get("key_symptoms", [])
        )
        
        return StoryResponse(
            success=result["success"],
            story=result["story"],
            author_name=result["author_name"],
            message=result["message"],
            model_used=result["model_used"],
            story_id=save_result.get("story_id")
        )
            
    except Exception as e:
        logger.error(f"Story transformation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create recovery story: {str(e)}")

@app.get("/stories")
async def get_approved_stories(limit: int = 20, skip: int = 0, random: bool = True):
    """Get approved recovery stories only"""
    try:
        stories = await StoryDatabase.get_recovery_stories(limit=limit, skip=skip)
        
        if random and len(stories) > limit:
            import random as rand
            rand.shuffle(stories)
            stories = stories[:limit]
        
        for story in stories:
            if 'match_percentage' in story:
                del story['match_percentage']
            if 'similarity_score' in story:
                del story['similarity_score']
            story.pop("user_id", None)
            story.pop("moderated_by", None)
            story.pop("moderation_notes", None)
        
        return {
            "success": True,
            "stories": stories,
            "count": len(stories)
        }
    except Exception as e:
        logger.error(f"Error getting stories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stories: {str(e)}")

@app.get("/crisis-resources")
async def get_crisis_resources():
    """Get crisis support resources (public endpoint)"""
    try:
        await CrisisSupport.log_crisis_interaction(
            interaction_type="crisis_resources_accessed"
        )
        
        return {
            "success": True,
            "resources": CrisisSupport.get_crisis_resources(),
            "message": "If you're in immediate danger, please call emergency services (911) or go to your nearest emergency room."
        }
        
    except Exception as e:
        logger.error(f"Error getting crisis resources: {e}")
        return {
            "success": True,
            "resources": CrisisSupport.get_crisis_resources()
        }

# Other existing endpoints
@app.post("/extract-symptoms", response_model=SymptomResponse)
async def extract_postnatal_symptoms(request: SymptomRequest):
    """Extract symptoms using Ollama and save to database"""
    
    if not request.experience.strip():
        raise HTTPException(status_code=400, detail="Experience cannot be empty")
    
    try:
        symptom_data = extract_symptoms(
            experience=request.experience,
            feelings=request.feelings
        )
        
        insights = get_symptom_insights(symptom_data)
        
        try:
            save_result = await SymptomDatabase.save_symptom_extraction(
                experience=request.experience,
                feelings=request.feelings,
                symptoms_identified=symptom_data.get("symptoms_identified", []),
                severity_indicators=symptom_data.get("severity_indicators", []),
                categories_affected=symptom_data.get("categories_affected", []),
                key_concerns=symptom_data.get("key_concerns", []),
                extraction_method=symptom_data.get("extraction_method", "unknown"),
                insights=insights
            )
            
            if save_result["success"]:
                logger.info(f"Symptom extraction saved with ID: {save_result['extraction_id']}")
            else:
                logger.error(f"Failed to save symptom extraction: {save_result['message']}")
                
        except Exception as db_error:
            logger.error(f"Database save error for symptom extraction: {str(db_error)}")
        
        return SymptomResponse(
            success=True,
            symptoms_identified=symptom_data.get("symptoms_identified", []),
            severity_indicators=symptom_data.get("severity_indicators", ["mild"]),
            categories_affected=symptom_data.get("categories_affected", []),
            key_concerns=symptom_data.get("key_concerns", []),
            extraction_method=symptom_data.get("extraction_method", "unknown"),
            insights=insights,
            message=f"Extracted {len(symptom_data.get('symptoms_identified', []))} symptoms using {symptom_data.get('extraction_method', 'unknown')} method and saved to database"
        )
        
    except Exception as e:
        logger.error(f"Symptom extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract symptoms: {str(e)}")

@app.post("/search-similar")
async def search_similar_stories(request: SearchRequest):
    """Search for similar recovery stories"""
    try:
        stories = await StoryDatabase.search_recovery_stories(request.query, limit=10)
        
        return {
            "success": True,
            "message": f"Found {len(stories)} recovery stories similar to: '{request.query}'",
            "results": stories
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "success": False,
            "message": f"Error searching for stories: {str(e)}",
            "results": []
        }

@app.get("/stories/{story_id}")
async def get_story(story_id: str):
    """Get a specific story by ID"""
    try:
        story = await StoryDatabase.get_story_by_id(story_id)
        if story:
            if 'match_percentage' in story:
                del story['match_percentage']
            if 'similarity_score' in story:
                del story['similarity_score']
            
            return {"success": True, "story": story}
        else:
            raise HTTPException(status_code=404, detail="Story not found")
    except Exception as e:
        logger.error(f"Error getting story {story_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get story: {str(e)}")

@app.get("/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        stats = await StoryDatabase.get_database_stats()
        symptom_patterns = await SymptomDatabase.get_symptom_patterns()
        
        return {
            "database_stats": stats,
            "symptom_patterns": symptom_patterns
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/models/test")
async def test_models():
    """Test Ollama connection and models"""
    
    ollama_connected, ollama_info = validate_ollama_connection()
    
    test_results = []
    if ollama_connected:
        for model_name in MODELS[:2]:
            result = test_model_connection(model_name)
            test_results.append(result)
    
    return {
        "success": ollama_connected and any(r["success"] for r in test_results),
        "ollama_connected": ollama_connected,
        "ollama_info": ollama_info,
        "available_models": MODELS,
        "test_results": test_results,
        "instructions": "Run 'ollama pull phi4' to install the main model"
    }

# Moderation endpoints (for moderators/admins)
@app.get("/moderation/pending")
async def get_pending_stories(
    current_user: dict = Depends(get_current_active_user),
    limit: int = 20
):
    """Get stories pending moderation (moderators only)"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        pending_stories = await ModerationDatabase.get_pending_stories(limit=limit)
        
        return {
            "success": True,
            "pending_stories": pending_stories,
            "count": len(pending_stories)
        }
        
    except Exception as e:
        logger.error(f"Error getting pending stories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pending stories")

@app.post("/moderation/approve/{story_id}")
async def approve_story(
    story_id: str,
    notes: str = "",
    current_user: dict = Depends(get_current_active_user)
):
    """Approve a pending story (moderators only)"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        result = await ModerationDatabase.approve_story(
            story_id=story_id,
            moderator_id=current_user["id"],
            notes=notes
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Story approved and published",
                "published_story_id": result["published_story_id"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving story: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve story")
    
# Add this endpoint to your main.py file

@app.post("/moderation/reject/{story_id}")
async def reject_story(
    story_id: str,
    reason: str = "Does not meet community guidelines",
    current_user: dict = Depends(get_current_active_user)
):
    """Reject a pending story (moderators only)"""
    
    if current_user.get("role") not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get the pending story
        pending_story = await mongodb.database.pending_stories.find_one(
            {"_id": ObjectId(story_id)}
        )
        
        if not pending_story:
            return {"success": False, "message": "Story not found"}
        
        # Move to rejected stories collection (for record keeping)
        rejected_story = pending_story.copy()
        rejected_story["status"] = "rejected"
        rejected_story["rejected_by"] = current_user["id"]
        rejected_story["rejected_at"] = datetime.utcnow()
        rejected_story["rejection_reason"] = reason
        del rejected_story["_id"]
        
        # Insert into rejected_stories collection
        await mongodb.database.rejected_stories.insert_one(rejected_story)
        
        # Remove from pending
        await mongodb.database.pending_stories.delete_one({"_id": ObjectId(story_id)})
        
        logger.info(f"Story {story_id} rejected by {current_user['email']}")
        
        return {
            "success": True,
            "message": "Story rejected and removed from queue"
        }
        
    except Exception as e:
        logger.error(f"Error rejecting story: {e}")
        return {"success": False, "message": "Failed to reject story"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )