"""
nlp_engine.py - SmartComplaint AI Priority & Categorization Engine
Implements custom Python NLP rules for civic complaint analysis, scoring,
categorization, urgency detection, and explainable AI signals.
"""

import re

# Keyword Dictionaries with weights
CRITICAL_KEYWORDS = {
    'fire', 'gas leak', 'building collapse', 'electrocution', 'explosive',
    'chemical spill', 'live wire', 'structural failure', 'flood emergency',
    'landslide', 'toxic leak', 'bridge collapse', 'life threatening',
    'explosion', 'short circuit fire', 'major accident', 'gas pipeline burst'
}

HIGH_KEYWORDS = {
    'water pipe burst', 'power failure', 'sewage overflow', 'road cave-in',
    'traffic signal failure', 'water contamination', 'open manhole',
    'blackout', 'drainage blockage', 'main road blocked', 'bridge damage',
    'water supply cut', 'sewer line burst', 'high voltage wire', 'wall collapse',
    'transformer explosion'
}

MEDIUM_KEYWORDS = {
    'garbage accumulation', 'garbage', 'trash', 'waste', 'street light broken',
    'streetlight', 'noise pollution', 'pothole', 'road maintenance',
    'illegal dumping', 'water leakage', 'stray animals', 'park damage',
    'illegal parking', 'traffic congestion', 'broken sidewalk', 'drain smell',
    'dirty water', 'overflowing bin'
}

LOW_KEYWORDS = {
    'suggestion', 'inquiry', 'minor issue', 'cosmetic repair', 'park bench',
    'sign board', 'clean-up request', 'tree trimming', 'garden maintenance',
    'paint scuff', 'notice board', 'feedback'
}

URGENCY_PHRASES = {
    'please help', 'very urgent', 'immediately', 'danger', 'hazard',
    'severe risk', 'asap', 'emergency', 'crisis', 'critical', 'blocking traffic',
    'public risk', 'active hazard', 'life threat', 'help urgently', 'at risk'
}

CATEGORY_KEYWORDS = {
    'Safety & Security': {
        'fire', 'gas leak', 'live wire', 'building collapse', 'electrocution',
        'crime', 'hazard', 'safety', 'security', 'theft', 'wall collapse',
        'explosion', 'emergency'
    },
    'Health & Sanitation': {
        'sewage', 'garbage', 'trash', 'waste', 'contamination', 'toxic',
        'dirty water', 'drainage', 'sanitation', 'smell', 'mosquitoes',
        'dengue', 'overflowing bin', 'unhygienic'
    },
    'Water & Utilities': {
        'water pipe', 'water supply', 'water leak', 'leakage', 'power failure',
        'blackout', 'electricity', 'transformer', 'pipeline', 'no water',
        'voltage', 'utility'
    },
    'Infrastructure & Roads': {
        'pothole', 'road', 'bridge', 'traffic signal', 'footpath', 'street light',
        'streetlight', 'manhole', 'cave-in', 'sidewalk', 'construction',
        'pavement', 'asphalt'
    },
    'Environment & Public Spaces': {
        'noise', 'park', 'tree', 'pollution', 'animals', 'stray', 'greenery',
        'garden', 'bench', 'public space', 'litter'
    }
}

CATEGORY_MULTIPLIERS = {
    'Safety & Security': 1.20,
    'Health & Sanitation': 1.10,
    'Water & Utilities': 1.05,
    'Infrastructure & Roads': 1.00,
    'Environment & Public Spaces': 1.00
}


def normalize_text(text: str) -> str:
    """Normalize text: convert to lowercase and strip punctuation."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def analyze_complaint(title: str, description: str, explicit_category: str = None) -> dict:
    """
    Analyzes complaint title and description using custom NLP rules.
    Returns score (0-100), priority level, category, urgency, detected signals,
    recommended handling, and explainable AI factors.
    """
    combined_text = normalize_text(f"{title} {description}")
    
    raw_score = 0
    detected_signals = []
    explanation_factors = []

    # 1. Keyword Scoring
    crit_matches = [kw for kw in CRITICAL_KEYWORDS if kw in combined_text]
    high_matches = [kw for kw in HIGH_KEYWORDS if kw in combined_text]
    med_matches = [kw for kw in MEDIUM_KEYWORDS if kw in combined_text]
    low_matches = [kw for kw in LOW_KEYWORDS if kw in combined_text]

    if crit_matches:
        raw_score += 45
        detected_signals.append("Critical hazard term detected")
        explanation_factors.append(f"✓ Critical keyword detected: '{crit_matches[0]}'")
    elif high_matches:
        raw_score += 30
        detected_signals.append("High severity infrastructure issue")
        explanation_factors.append(f"✓ High urgency keyword detected: '{high_matches[0]}'")
    elif med_matches:
        raw_score += 18
        detected_signals.append("Standard civic maintenance issue")
        explanation_factors.append(f"✓ General civic issue keyword: '{med_matches[0]}'")
    elif low_matches:
        raw_score += 8
        detected_signals.append("Routine maintenance / inquiry")
        explanation_factors.append(f"✓ Routine inquiry keyword: '{low_matches[0]}'")
    else:
        raw_score += 12
        explanation_factors.append("✓ General complaint description analyzed")

    # Additional matching bonuses for multiple keywords
    total_keyword_matches = len(crit_matches) + len(high_matches) + len(med_matches)
    if total_keyword_matches > 1:
        bonus = min(15, (total_keyword_matches - 1) * 7)
        raw_score += bonus
        explanation_factors.append(f"✓ Compound issue bonus: +{bonus} pts for multiple risk terms")

    # 2. Urgency Detection
    urgency_matches = [u for u in URGENCY_PHRASES if u in combined_text]
    if urgency_matches:
        raw_score += 20
        detected_signals.append("Urgent citizen call-to-action")
        explanation_factors.append(f"✓ Urgency phrase detected: '{urgency_matches[0]}'")

    # 3. Description Depth & Length Bonus
    desc_length = len(description.strip()) if description else 0
    if desc_length > 200:
        raw_score += 10
        explanation_factors.append("✓ High description detail bonus: +10 pts")
        detected_signals.append("Comprehensive description detail")
    elif desc_length > 80:
        raw_score += 5
        explanation_factors.append("✓ Adequate detail bonus: +5 pts")

    # 4. Category Detection
    detected_category = explicit_category
    if not detected_category or detected_category == "Auto-Detect" or detected_category == "Other":
        cat_scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            cat_score = sum(1 for kw in keywords if kw in combined_text)
            if cat_score > 0:
                cat_scores[cat] = cat_score
        
        if cat_scores:
            detected_category = max(cat_scores, key=cat_scores.get)
        else:
            detected_category = "Infrastructure & Roads"  # default fallback

    # 5. Category Multiplier
    multiplier = CATEGORY_MULTIPLIERS.get(detected_category, 1.00)
    if multiplier > 1.0:
        explanation_factors.append(f"✓ Category risk multiplier applied: {detected_category} ({multiplier}x)")
        detected_signals.append(f"High risk domain: {detected_category}")

    final_score = int(round(raw_score * multiplier))
    final_score = max(5, min(99, final_score))  # clamp between 5 and 99

    # Override for explicit extreme critical phrases
    if crit_matches and urgency_matches:
        final_score = max(85, final_score)

    # 6. Priority Level & Handling Determination
    if final_score >= 81:
        priority_level = "CRITICAL"
        priority_badge = "🔴 CRITICAL"
        urgency = "Critical"
        risk_level = "Severe Risk"
        recommended_handling = "Immediate Emergency Dispatch (0–2 Hours)"
    elif final_score >= 61:
        priority_level = "HIGH"
        priority_badge = "🟠 HIGH"
        urgency = "High"
        risk_level = "High Risk"
        recommended_handling = "Priority Rapid Field Team (2–6 Hours)"
    elif final_score >= 31:
        priority_level = "MEDIUM"
        priority_badge = "🟡 MEDIUM"
        urgency = "Medium"
        risk_level = "Moderate Risk"
        recommended_handling = "Standard Municipal Queue (24–48 Hours)"
    else:
        priority_level = "LOW"
        priority_badge = "🟢 LOW"
        urgency = "Low"
        risk_level = "Low Risk"
        recommended_handling = "Routine Inspection & Maintenance (3–5 Days)"

    if not detected_signals:
        detected_signals = ["Standard Civic Report", "Public Infrastructure"]

    return {
        "score": final_score,
        "priority": priority_level,
        "priority_badge": priority_badge,
        "category": detected_category,
        "urgency": urgency,
        "risk_level": risk_level,
        "recommended_handling": recommended_handling,
        "detected_signals": detected_signals,
        "explanation_factors": explanation_factors,
        "multiplier": multiplier
    }


if __name__ == "__main__":
    import json
    # Quick self-test
    test1 = analyze_complaint("Gas leak and fire near school", "Gas pipe burst in residential area, please help immediately!")
    print("Test 1 (Critical): Score =", test1['score'], "Priority =", test1['priority'])
    
    test2 = analyze_complaint("Streetlight broken", "The streetlight on 4th main road is not working.")
    print("Test 2 (Medium): Score =", test2['score'], "Priority =", test2['priority'])

