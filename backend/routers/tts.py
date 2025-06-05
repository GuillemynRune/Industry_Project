from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from services.tts_service import TTSService
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["text-to-speech"])
limiter = Limiter(key_func=get_remote_address)

tts_service = TTSService()

class TTSRequest(BaseModel):
    text: str
    voice: str = "sarah"

@router.post("/generate")
@limiter.limit("10/minute")  # Prevent abuse
async def generate_speech(request: Request, tts_request: TTSRequest):
    """Generate speech from text using ElevenLabs"""
    
    if not tts_request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(tts_request.text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 characters)")
    
    audio_data = await tts_service.generate_speech(
        text=tts_request.text, 
        voice=tts_request.voice
    )
    
    if audio_data is None:
        raise HTTPException(status_code=500, detail="Failed to generate speech")
    
    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        }
    )

@router.get("/voices")
async def get_voices():
    """Get available voice options"""
    return {
        "voices": tts_service.get_available_voices(),
        "default": "sarah"
    }