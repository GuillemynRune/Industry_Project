"""
Symptom extraction service using Ollama
"""

import logging
from typing import List, Dict, Optional
from .ollama_client import query_ollama_model, OLLAMA_MODEL, MODELS

logger = logging.getLogger(__name__)

# Common postnatal symptoms to look for
POSTNATAL_SYMPTOMS = {
    "emotional": [
        "anxiety", "depression", "mood swings", "irritability", "crying spells",
        "feeling overwhelmed", "guilt", "shame", "anger", "fear", "worry",
        "sadness", "hopelessness", "panic", "intrusive thoughts"
    ],
    "physical": [
        "fatigue", "exhaustion", "sleep deprivation", "headaches", "muscle tension",
        "appetite changes", "weight changes", "physical pain", "weakness"
    ],
    "cognitive": [
        "brain fog", "memory problems", "concentration issues", "confusion",
        "difficulty making decisions", "racing thoughts", "forgetfulness"
    ],
    "social": [
        "isolation", "loneliness", "relationship problems", "difficulty bonding",
        "social withdrawal", "feeling disconnected", "lack of support"
    ],
    "behavioral": [
        "sleep problems", "eating changes", "avoiding activities", "perfectionism",
        "obsessive behaviors", "checking behaviors", "restlessness"
    ]
}

def create_symptom_extraction_prompt(experience: str, feelings: str) -> str:
    """Create prompt for extracting symptoms from experience"""
    return f"""You are a healthcare assistant specializing in postnatal mental health. Extract symptoms from the user's experience and feelings.

Available symptom categories:
- Emotional: anxiety, depression, mood swings, guilt, fear, etc.
- Physical: fatigue, sleep issues, appetite changes, etc.
- Cognitive: brain fog, memory problems, concentration issues, etc.
- Social: isolation, bonding difficulties, relationship issues, etc.
- Behavioral: sleep problems, perfectionism, avoidance, etc.

Return ONLY a JSON object with this exact format:
{{
    "symptoms_identified": ["symptom1", "symptom2", "symptom3"],
    "severity_indicators": ["mild", "moderate", "severe"],
    "categories_affected": ["emotional", "physical", "cognitive", "social", "behavioral"],
    "key_concerns": ["primary concern 1", "primary concern 2"]
}}

Experience: {experience}

Feelings: {feelings}

Extract symptoms from the above text and return only the JSON:"""

def extract_symptoms(experience: str, feelings: str) -> Dict:
    """Extract symptoms from user's experience and feelings using Ollama"""
    
    try:
        prompt = create_symptom_extraction_prompt(experience, feelings)
        
        # Try models for symptom extraction
        for model_name in MODELS[:2]:  # Try first 2 models
            try:
                logger.info(f"Extracting symptoms with model: {model_name}")
                
                generated_text = query_ollama_model(model_name, prompt, max_tokens=200)
                
                if generated_text:
                    response = generated_text.strip()
                    
                    # Try to parse JSON response
                    try:
                        import json
                        # Find JSON in response
                        json_start = response.find('{')
                        json_end = response.rfind('}') + 1
                        
                        if json_start != -1 and json_end > json_start:
                            json_str = response[json_start:json_end]
                            symptom_data = json.loads(json_str)
                            symptom_data["extraction_method"] = f"ollama_{model_name}"
                            return symptom_data
                    except json.JSONDecodeError:
                        logger.warning(f"JSON parsing failed for model {model_name}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Symptom extraction failed with {model_name}: {str(e)}")
                continue
        
        # Fallback: Rule-based symptom extraction
        logger.info("Using fallback rule-based symptom extraction")
        return extract_symptoms_rule_based(experience, feelings)
        
    except Exception as e:
        logger.error(f"Error in symptom extraction: {str(e)}")
        return extract_symptoms_rule_based(experience, feelings)

def extract_symptoms_rule_based(experience: str, feelings: str) -> Dict:
    """Fallback rule-based symptom extraction"""
    
    combined_text = f"{experience} {feelings}".lower()
    
    identified_symptoms = []
    categories_affected = []
    severity_words = ["exhausted", "overwhelming", "terrible", "awful", "severe", "intense"]
    
    # Check each category for symptoms
    for category, symptoms in POSTNATAL_SYMPTOMS.items():
        category_found = False
        for symptom in symptoms:
            if symptom.lower() in combined_text:
                identified_symptoms.append(symptom)
                category_found = True
        
        if category_found and category not in categories_affected:
            categories_affected.append(category)
    
    # Determine severity based on language intensity
    severity_count = sum(1 for word in severity_words if word in combined_text)
    if severity_count >= 3:
        severity = ["severe"]
    elif severity_count >= 1:
        severity = ["moderate"]
    else:
        severity = ["mild"]
    
    # Extract key concerns
    key_concerns = []
    if "sleep" in combined_text or "tired" in combined_text:
        key_concerns.append("sleep deprivation")
    if "bond" in combined_text or "connect" in combined_text:
        key_concerns.append("bonding difficulties")
    if "alone" in combined_text or "isolated" in combined_text:
        key_concerns.append("social isolation")
    if "anxious" in combined_text or "worry" in combined_text:
        key_concerns.append("anxiety")
    if "sad" in combined_text or "depressed" in combined_text:
        key_concerns.append("mood concerns")
    
    return {
        "symptoms_identified": identified_symptoms[:10],
        "severity_indicators": severity,
        "categories_affected": categories_affected,
        "key_concerns": key_concerns[:5],
        "extraction_method": "rule_based",
        "total_symptoms_found": len(identified_symptoms)
    }

def get_symptom_insights(symptom_data: Dict) -> Dict:
    """Generate insights from extracted symptoms"""
    
    insights = {
        "risk_level": "low",
        "recommendations": [],
        "support_resources": [],
        "next_steps": []
    }
    
    symptom_count = len(symptom_data.get("symptoms_identified", []))
    categories_count = len(symptom_data.get("categories_affected", []))
    severity = symptom_data.get("severity_indicators", ["mild"])[0]
    
    # Determine risk level
    if symptom_count >= 8 or categories_count >= 4 or severity == "severe":
        insights["risk_level"] = "high"
        insights["recommendations"] = [
            "Consider speaking with a healthcare provider",
            "Reach out to a mental health professional",
            "Contact postnatal support services"
        ]
    elif symptom_count >= 4 or categories_count >= 2 or severity == "moderate":
        insights["risk_level"] = "medium"
        insights["recommendations"] = [
            "Consider additional support resources",
            "Talk to other parents in similar situations",
            "Practice self-care strategies"
        ]
    else:
        insights["recommendations"] = [
            "Continue monitoring your wellbeing",
            "Connect with other parents",
            "Prioritize rest when possible"
        ]
    
    # Add resources based on symptoms
    key_concerns = symptom_data.get("key_concerns", [])
    if any("anxiety" in concern for concern in key_concerns):
        insights["support_resources"].append("Anxiety support groups")
    if any("sleep" in concern for concern in key_concerns):
        insights["support_resources"].append("Sleep support resources")
    if any("bonding" in concern for concern in key_concerns):
        insights["support_resources"].append("Parent-baby bonding support")
    
    return insights