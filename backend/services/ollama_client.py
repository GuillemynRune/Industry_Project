"""
Ollama API client for local model interactions
"""

import requests
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
MODELS = ["qwen2.5:3b"]

def query_ollama_model(model_name: str, prompt: str, max_tokens: int = 300) -> str:
    """Query Ollama model running locally"""
    
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        else:
            logger.error(f"Ollama API Error: {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Ollama error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        logger.error("Connection error - is Ollama running?")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama. Make sure it's running on localhost:11434")
        
    except requests.exceptions.Timeout:
        logger.error("Timeout error")
        raise HTTPException(status_code=504, detail="Ollama request timed out")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Request failed: {str(e)}")

def validate_ollama_connection() -> tuple[bool, dict]:
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            return True, {"available_models": available_models}
        else:
            return False, {"error": f"Status code: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
        return False, {"error": str(e)}

def test_model_connection(model_name: str = None) -> dict:
    """Test connection to specific Ollama model"""
    test_model = model_name or OLLAMA_MODEL
    
    try:
        result = query_ollama_model(test_model, "Hello, this is a test.", max_tokens=20)
        return {
            "success": True,
            "model": test_model,
            "result": result[:100] + "..." if len(result) > 100 else result
        }
    except Exception as e:
        return {
            "success": False,
            "model": test_model,
            "error": str(e)
        }