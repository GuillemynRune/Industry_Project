from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from database.models.users import UserDatabase
import os
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
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

# Routes
@router.post("/register")
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

@router.post("/login", response_model=Token)
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