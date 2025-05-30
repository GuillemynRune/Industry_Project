from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Set
from database.models.users import UserDatabase
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import secrets
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# JWT Configuration - Enhanced Security
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Token blacklist for logout functionality
BLACKLISTED_TOKENS: Set[str] = set()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Enhanced Pydantic models with validation
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    agrees_to_terms: bool = True
    age_verified: bool = True

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        # Additional email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower()

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
    expires_in: int

# Helper functions
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
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def blacklist_token(token: str):
    """Add token to blacklist"""
    BLACKLISTED_TOKENS.add(token)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted
        if token in BLACKLISTED_TOKENS:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_email is None or token_type != "access":
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT Error: {e}")
        raise credentials_exception
    
    user = await UserDatabase.get_user_by_email(user_email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Routes with enhanced security
@router.post("/register")
@limiter.limit("3/minute")  # Limit registration attempts
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user account with enhanced validation"""
    
    if not user_data.age_verified:
        raise HTTPException(status_code=400, detail="You must be 18 or older to use this service")
    
    if not user_data.agrees_to_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms of service")
    
    try:
        # Hash password with high rounds for security
        password_hash = get_password_hash(user_data.password)
        
        result = await UserDatabase.create_user(
            email=user_data.email,
            password_hash=password_hash,
            display_name=user_data.display_name
        )
        
        if result["success"]:
            logger.info(f"New user registered: {user_data.email}")
            return {
                "success": True,
                "message": "Account created successfully! You can now log in.",
                "user_id": result["user_id"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create account")

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # Limit login attempts to prevent brute force
async def login_user(request: Request, user_data: UserLogin):
    """Login user and return access token with enhanced security"""
    
    try:
        user = await UserDatabase.get_user_by_email(user_data.email)
        
        if not user:
            # Log failed login attempt
            logger.warning(f"Login attempt for non-existent user: {user_data.email}")
            # Same error message to prevent user enumeration
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        if not verify_password(user_data.password, user["password_hash"]):
            logger.warning(f"Failed login attempt for user: {user_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        if not user.get("is_active", False):
            raise HTTPException(status_code=400, detail="Account is deactivated")
        
        # Update last login
        await UserDatabase.update_last_login(user_data.email)
        
        # Create token with shorter expiry for security
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"]},
            expires_delta=access_token_expires
        )
        
        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user.get("display_name", "Anonymous"),
            created_at=user["created_at"],
            is_active=user["is_active"],
            role=user.get("role", "user")
        )
        
        logger.info(f"Successful login for user: {user_data.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/logout")
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user by blacklisting token"""
    try:
        token = credentials.credentials
        blacklist_token(token)
        
        logger.info("User logged out successfully")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/me", response_model=UserResponse)
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

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_active_user)):
    """Refresh access token"""
    try:
        # Create new token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": current_user["email"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh token")