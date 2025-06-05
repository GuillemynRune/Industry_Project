import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TTSService:
    """ElevenLabs Text-to-Speech service"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Popular voice IDs for empathetic content
        self.voices = {
            "sarah": "EXAVITQu4vr4xnSDxMaL",  # Warm, empathetic
            "rachel": "21m00Tcm4TlvDq8ikWAM", # Clear, supportive
            "bella": "EXAVITQu4vr4xnSDxMaL",  # Gentle, caring
        }
    
    async def generate_speech(self, text: str, voice: str = "sarah") -> Optional[bytes]:
        """Generate speech audio from text"""
        if not self.api_key:
            logger.error("ElevenLabs API key not configured")
            return None
        
        if not text.strip():
            return None
        
        voice_id = self.voices.get(voice, self.voices["sarah"])
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.api_key
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.6,
                            "similarity_boost": 0.8,
                            "style": 0.4,
                            "use_speaker_boost": True
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"ElevenLabs API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None
    
    def get_available_voices(self):
        """Get list of available voices"""
        return list(self.voices.keys())