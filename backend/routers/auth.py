from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Set
from database.models.users import UserDatabase
from services.email_service import EmailService
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Token blacklist
BLACKLISTED_TOKENS: Set[str] = set()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    agrees_to_terms: bool = True
    age_verified: bool = True

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
            raise ValueError('Password must contain letters and numbers')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
            raise ValueError('Password must contain letters and numbers')
        return v

class AccountDeletionRequest(BaseModel):
    email: EmailStr
    password: str  # Require password confirmation for security

class AccountDeletionConfirm(BaseModel):
    token: str
    confirmation_text: str  # User must type specific text to confirm

    @validator('confirmation_text')
    def validate_confirmation(cls, v):
        if v.strip().lower() != "delete my account":
            raise ValueError('You must type "DELETE MY ACCOUNT" to confirm deletion')
        return v

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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def blacklist_token(token: str):
    BLACKLISTED_TOKENS.add(token)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        if token in BLACKLISTED_TOKENS:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_email is None or token_type != "access":
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
@limiter.limit("3/minute")
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user account"""
    
    if not user_data.age_verified or not user_data.agrees_to_terms:
        raise HTTPException(status_code=400, detail="Age verification and terms agreement required")
    
    password_hash = get_password_hash(user_data.password)
    
    result = await UserDatabase.create_user(
        email=user_data.email,
        password_hash=password_hash,
        display_name=user_data.display_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    logger.info(f"New user registered: {user_data.email}")
    return {
        "success": True,
        "message": "Account created successfully! You can now log in.",
        "user_id": result["user_id"]
    }

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_user(request: Request, user_data: UserLogin):
    """Login user and return access token"""
    
    user = await UserDatabase.get_user_by_email(user_data.email)
    
    if not user or not verify_password(user_data.password, user["password_hash"]):
        logger.warning(f"Failed login attempt for: {user_data.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Account is deactivated")
    
    await UserDatabase.update_last_login(user_data.email)
    
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
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/forgot-password")
@limiter.limit("3/15minutes")
async def forgot_password(request: Request, reset_request: PasswordResetRequest):
    """Request password reset token"""
    
    # Clean up expired tokens first
    await UserDatabase.clear_expired_reset_tokens()
    
    # Check if user exists
    user = await UserDatabase.get_user_by_email(reset_request.email)
    if not user:
        # Return success even if user doesn't exist (security best practice)
        return {
            "success": True,
            "message": "If an account with that email exists, we've sent password reset instructions."
        }
    
    # Generate reset token
    reset_token = await UserDatabase.create_password_reset_token(reset_request.email)
    if not reset_token:
        raise HTTPException(status_code=500, detail="Unable to generate reset token")
    
    # Send email
    email_sent = await EmailService.send_password_reset_email(
        email=reset_request.email,
        reset_token=reset_token,
        user_name=user.get("display_name", "there")
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Unable to send reset email")
    
    logger.info(f"Password reset email sent to: {reset_request.email}")
    
    return {
        "success": True,
        "message": "If an account with that email exists, we've sent password reset instructions."
    }

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, reset_data: PasswordReset):
    """Reset password using valid token"""
    
    # Verify token
    user = await UserDatabase.verify_reset_token(reset_data.token)
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired reset token. Please request a new password reset."
        )
    
    # Hash new password
    new_password_hash = get_password_hash(reset_data.new_password)
    
    # Update password
    success = await UserDatabase.reset_password(reset_data.token, new_password_hash)
    if not success:
        raise HTTPException(status_code=500, detail="Unable to reset password")
    
    logger.info(f"Password reset successful for user: {user['email']}")
    
    return {
        "success": True,
        "message": "Password reset successful! You can now log in with your new password."
    }


@router.post("/delete-account")
@limiter.limit("3/hour")
async def delete_account(request: Request, deletion_request: AccountDeletionRequest):
    """Delete account immediately upon credential verification"""
    user = await UserDatabase.get_user_by_email(deletion_request.email)
    if not user or not verify_password(deletion_request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    try:
        success = await UserDatabase.delete_user_account(user_id=user["id"])
        if not success:
            raise HTTPException(status_code=500, detail="Unable to delete account")
        
        logger.info(f"Account successfully deleted for user: {user['email']}")
        return {
            "success": True,
            "message": "Your account has been permanently deleted."
        }
    
    except Exception as e:
        logger.error(f"Account deletion failed for user {user['email']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Account deletion failed")
    

@router.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user by blacklisting token"""
    blacklist_token(credentials.credentials)
    return {"message": "Successfully logged out"}

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