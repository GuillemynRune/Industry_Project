"""
Symptom extraction service using Ollama
"""

import logging
from typing import List, Dict
from .ollama_client import query_ollama_model, MODELS

logger = logging.getLogger(__name__)

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
    """Extract symptoms from user's experience using Ollama with fallback"""
    
    prompt = create_symptom_extraction_prompt(experience, feelings)
    
    # Try AI models first
    for model_name in MODELS[:2]:
        try:
            generated_text = query_ollama_model(model_name, prompt, max_tokens=200)
            
            if generated_text:
                # Parse JSON response
                import json
                json_start = generated_text.find('{')
                json_end = generated_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = generated_text[json_start:json_end]
                    symptom_data = json.loads(json_str)
                    symptom_data["extraction_method"] = f"ollama_{model_name}"
                    return symptom_data
                        
        except Exception as e:
            logger.warning(f"Symptom extraction failed with {model_name}: {str(e)}")
            continue
    
    # Fallback to rule-based extraction
    return extract_symptoms_rule_based(experience, feelings)

def extract_symptoms_rule_based(experience: str, feelings: str) -> Dict:
    """Rule-based symptom extraction fallback"""
    
    combined_text = f"{experience} {feelings}".lower()
    
    # Symptom categories
    symptom_keywords = {
        "emotional": ["anxiety", "depression", "mood swings", "irritability", "crying", "overwhelmed", "guilt", "shame", "anger", "fear", "worry", "sadness", "hopeless", "panic"],
        "physical": ["fatigue", "exhaustion", "sleep deprivation", "headaches", "muscle tension", "appetite changes", "weight changes", "pain", "weakness"],
        "cognitive": ["brain fog", "memory problems", "concentration", "confusion", "decisions", "racing thoughts", "forgetfulness"],
        "social": ["isolation", "loneliness", "relationship problems", "bonding", "withdrawal", "disconnected", "support"],
        "behavioral": ["sleep problems", "eating changes", "avoiding", "perfectionism", "obsessive", "checking", "restless"]
    }
    
    identified_symptoms = []
    categories_affected = []
    
    # Extract symptoms by category
    for category, keywords in symptom_keywords.items():
        category_found = False
        for keyword in keywords:
            if keyword in combined_text:
                identified_symptoms.append(keyword)
                category_found = True
        
        if category_found:
            categories_affected.append(category)
    
    # Determine severity
    severity_words = ["exhausted", "overwhelming", "terrible", "awful", "severe", "intense"]
    severity_count = sum(1 for word in severity_words if word in combined_text)
    
    if severity_count >= 3:
        severity = ["severe"]
    elif severity_count >= 1:
        severity = ["moderate"]
    else:
        severity = ["mild"]
    
    # Extract key concerns
    key_concerns = []
    concern_mapping = {
        "sleep deprivation": ["sleep", "tired"],
        "bonding difficulties": ["bond", "connect"],
        "social isolation": ["alone", "isolated"],
        "anxiety": ["anxious", "worry"],
        "mood concerns": ["sad", "depressed"]
    }
    
    for concern, keywords in concern_mapping.items():
        if any(keyword in combined_text for keyword in keywords):
            key_concerns.append(concern)
    
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
    
    symptom_count = len(symptom_data.get("symptoms_identified", []))
    categories_count = len(symptom_data.get("categories_affected", []))
    severity = symptom_data.get("severity_indicators", ["mild"])[0]
    
    insights = {"risk_level": "low", "recommendations": [], "support_resources": []}
    
    # Determine risk level and recommendations
    if symptom_count >= 8 or categories_count >= 4 or severity == "severe":
        insights.update({
            "risk_level": "high",
            "recommendations": [
                "Consider speaking with a healthcare provider",
                "Reach out to a mental health professional", 
                "Contact postnatal support services"
            ]
        })
    elif symptom_count >= 4 or categories_count >= 2 or severity == "moderate":
        insights.update({
            "risk_level": "medium",
            "recommendations": [
                "Consider additional support resources",
                "Talk to other parents in similar situations",
                "Practice self-care strategies"
            ]
        })
    else:
        insights["recommendations"] = [
            "Continue monitoring your wellbeing",
            "Connect with other parents",
            "Prioritize rest when possible"
        ]
    
    # Add targeted resources
    key_concerns = symptom_data.get("key_concerns", [])
    resources = []
    if any("anxiety" in concern for concern in key_concerns):
        resources.append("Anxiety support groups")
    if any("sleep" in concern for concern in key_concerns):
        resources.append("Sleep support resources")
    if any("bonding" in concern for concern in key_concerns):
        resources.append("Parent-baby bonding support")
    
    insights["support_resources"] = resources
    return insights