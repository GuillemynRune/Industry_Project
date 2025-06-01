"""
Ollama API client
Handles all interactions with local Ollama models
"""

import requests
import logging
from typing import Dict, Any
from fastapi import HTTPException
import os

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "phi4"  # The model you'll pull with Ollama

# Available models (you can add more as you install them)
MODELS = [
    "phi4",
    "llama3.2:3b",  # Alternative if you want to try others
    "gemma2:2b",    # Alternative smaller model
]

def query_ollama_model(model_name: str, prompt: str, max_tokens: int = 300) -> str:
    """Query Ollama model running locally"""
    
    try:
        logger.info(f"Querying local model: {model_name}")
        
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
            timeout=120  # Longer timeout for local inference
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '')
            logger.info(f"Generated text length: {len(generated_text)}")
            return generated_text
        else:
            logger.error(f"Ollama API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Ollama error: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error - is Ollama running?: {str(e)}")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama. Make sure it's running on localhost:11434")
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {str(e)}")
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
            logger.info(f"Ollama connected. Available models: {available_models}")
            return True, {"available_models": available_models}
        else:
            logger.error(f"Ollama connection failed: {response.status_code}")
            return False, {"error": f"Status code: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Ollama connection error: {e}")
        return False, {"error": str(e)}

def test_model_connection(model_name: str = None) -> dict:
    """Test connection to a specific Ollama model"""
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