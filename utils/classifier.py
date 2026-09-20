"""
Complaint classification.

classify_complaint() uses prompt engineering to ask the LLM to return a
structured JSON classification of a civic complaint: category, urgency,
department, and whether it is flood/drainage-related. Supports an optional
image (multimodal) alongside or instead of text description, using Gemini's
vision capability. If no LLM is configured (or the call fails), a
transparent keyword-based fallback is used for text input; image-only input
requires an LLM key, since the rule-based fallback cannot interpret images.

Life-threatening situations (fire, exposed live wires, gas leaks, structural
collapse) are treated as a distinct Emergency category and always forced to
High urgency, in both the LLM prompt and the rule-based fallback — this is
checked before general category matching so it can never be silently
downgraded by a routine keyword like "water" or "wire" alone.
"""

from utils.llm_helper import get_llm_json, get_llm_json_multimodal, llm_is_configured

CATEGORIES = [
    "Emergency/Life-Threatening",
    "Waterlogging/Drainage",
    "Garbage/Sanitation",
    "Streetlight",
    "Water Supply",
    "Road Damage",
    "Noise",
    "Public Safety",
    "Other",
]

DEPARTMENT_MAP = {
    "Emergency/Life-Threatening": "Emergency Services / Fire & Disaster Response",
    "Waterlogging/Drainage": "Drainage & Sewerage Dept.",
    "Garbage/Sanitation": "Solid Waste Management Dept.",
    "Streetlight": "Electrical (Street Lighting) Dept.",
    "Water Supply": "Water Supply Dept.",
    "Road Damage": "Roads & Engineering Dept.",
    "Noise": "Environment/Enforcement Dept.",
    "Public Safety": "Public Safety / Enforcement Dept.",
    "Other": "General Grievance Cell",
}

# Checked FIRST, before any other category — these always mean High urgency
# and route to Emergency Services, regardless of what else is in the text.
EMERGENCY_KEYWORDS = [
    "fire", "burning", "in flames", "flames", "explosion", "exploded",
    "gas leak", "gas smell", "smell of gas",
    "live wire", "exposed wire", "electric wire", "electrical wire",
    "wire hanging", "downed wire", "sparking wire", "sparking", "short circuit",
    "electrocut",
    "building collapse", "wall collapse", "collapsed", "roof caved in",
    "trapped", "life-threatening", "medical emergency",
]

FLOOD_KEYWORDS = [
    "waterlog", "water logg", "water clog", "clogg", "flood", "drain",
    "water overflow", "overflowing onto", "stagnat", "knee-deep", "ankle",
    "submerg", "choked",
]

CATEGORY_KEYWORDS = {
    "Waterlogging/Drainage": FLOOD_KEYWORDS,
    "Garbage/Sanitation": ["garbage", "trash", "smell", "waste", "bin"],
    "Streetlight": ["streetlight", "street light", "dark at night", "light"],
    "Water Supply": ["no water supply", "water supply", "pipeline"],
    "Road Damage": ["pothole", "road caved", "road damage", "caved in"],
    "Noise": ["noise", "loud", "construction noise"],
    "Public Safety": ["unsafe", "manhole", "stray dog", "dangerous"],
}

TEXT_PROMPT_TEMPLATE = """You are a civic complaint triage assistant for a city corporation in India.
Classify the following citizen complaint.

Complaint: "{description}"

Classification rules, in priority order:
1. If the complaint describes anything immediately life-threatening — fire, an exposed or live
   electrical wire (especially near water or in a waterlogged area, which is an electrocution risk),
   a gas leak, structural collapse, or someone trapped — classify it as category
   "Emergency/Life-Threatening" with urgency "High", no matter what else is in the text. This rule
   always wins over every other category.
2. Otherwise, classify normally by the best-fitting category and urgency.

Return STRICT JSON only, no extra text, in this exact shape:
{{
  "category": one of {categories},
  "urgency": one of ["Low", "Medium", "High"],
  "is_flood_related": true or false,
  "reason": "one short sentence explaining the classification"
}}
"""

IMAGE_PROMPT_TEMPLATE = """You are a civic complaint triage assistant for a city corporation in India.
A citizen has uploaded a photo of a civic issue{caption_clause}.
Look at the image and classify the issue it shows.

Classification rules, in priority order:
1. If the image or caption shows anything immediately life-threatening — fire, an exposed or live
   electrical wire (especially near water or in a waterlogged area, which is an electrocution risk),
   a gas leak, structural collapse, or someone trapped — classify it as category
   "Emergency/Life-Threatening" with urgency "High", no matter what else is visible. This rule always
   wins over every other category.
2. Otherwise, classify normally by the best-fitting category and urgency.

Return STRICT JSON only, no extra text, in this exact shape:
{{
  "category": one of {categories},
  "urgency": one of ["Low", "Medium", "High"],
  "is_flood_related": true or false,
  "reason": "one short sentence describing what you see in the image and why you classified it this way"
}}
"""


def _rule_based_classify(description: str) -> dict:
    text = description.lower()
    is_flood_related = any(kw in text for kw in FLOOD_KEYWORDS)
    is_emergency = any(kw in text for kw in EMERGENCY_KEYWORDS)

    if is_emergency:
        return {
            "category": "Emergency/Life-Threatening",
            "urgency": "High",
            "is_flood_related": is_flood_related,
            "reason": "Rule-based: matched a life-safety keyword (fire, exposed wire, gas leak, etc.) "
                      "— always treated as High urgency, regardless of other content.",
            "source": "rule-based",
        }

    category = "Other"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            category = cat
            break

    if is_flood_related or "unsafe" in text or "dangerous" in text or "fell" in text:
        urgency = "High"
    elif category in ("Garbage/Sanitation", "Water Supply", "Road Damage"):
        urgency = "Medium"
    else:
        urgency = "Low"

    return {
        "category": category,
        "urgency": urgency,
        "is_flood_related": is_flood_related,
        "reason": "Rule-based keyword match (no LLM configured or LLM call failed).",
        "source": "rule-based",
    }


def classify_complaint(description: str = "", image=None) -> dict:
    """
    description: free-text complaint (optional if image is given)
    image: a PIL.Image.Image object (optional if description is given)
    """
    description = (description or "").strip()

    if image is not None:
        if not llm_is_configured():
            return {
                "category": "Other",
                "urgency": "Medium",
                "is_flood_related": False,
                "reason": "Image submitted but no LLM key is configured, so the image "
                          "could not be analyzed. Add a description or configure "
                          "GOOGLE_API_KEY/GROQ_API_KEY.",
                "source": "unavailable",
                "department": DEPARTMENT_MAP["Other"],
            }
        caption_clause = f', with the caption: "{description}"' if description else ""
        prompt = IMAGE_PROMPT_TEMPLATE.format(caption_clause=caption_clause, categories=CATEGORIES)
        result = get_llm_json_multimodal(prompt, image)
        if result and "category" in result and "urgency" in result:
            result.setdefault("is_flood_related", result["category"] == "Waterlogging/Drainage")
            result["source"] = "llm-vision"
            result["department"] = DEPARTMENT_MAP.get(result["category"], "General Grievance Cell")
            return result
        if not description:
            return {
                "category": "Other",
                "urgency": "Medium",
                "is_flood_related": False,
                "reason": "Image analysis failed and no text description was provided.",
                "source": "unavailable",
                "department": DEPARTMENT_MAP["Other"],
            }

    if llm_is_configured() and description:
        prompt = TEXT_PROMPT_TEMPLATE.format(description=description, categories=CATEGORIES)
        result = get_llm_json(prompt)
        if result and "category" in result and "urgency" in result:
            result.setdefault("is_flood_related", result["category"] == "Waterlogging/Drainage")
            result["source"] = "llm"
            result["department"] = DEPARTMENT_MAP.get(result["category"], "General Grievance Cell")
            return result

    result = _rule_based_classify(description) if description else {
        "category": "Other",
        "urgency": "Low",
        "is_flood_related": False,
        "reason": "No description or usable image provided.",
        "source": "rule-based",
    }
    result["department"] = DEPARTMENT_MAP.get(result["category"], "General Grievance Cell")
    return result
