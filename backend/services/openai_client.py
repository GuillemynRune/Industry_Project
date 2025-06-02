import os
from openai import OpenAI
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Available OpenAI models
MODELS = ["gpt-3.5-turbo", "gpt-4o-mini"]

def query_openai_model(model_name: str, prompt: str, max_tokens: int = 300) -> str:
    try:
        response = client.chat.completions.create(
            model=model_name,  # Pass model as parameter
            messages=[
                {"role": "system", "content": "You are a compassionate assistant helping people share their mental health recovery experiences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")