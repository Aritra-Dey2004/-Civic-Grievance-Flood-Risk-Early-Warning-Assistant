"""
Hybrid LLM helper.

Tries Gemini first (if GOOGLE_API_KEY is set), then Groq (if GROQ_API_KEY is
set) for text-only calls. If neither key is configured, get_llm_response()
returns None so the caller can fall back to a rule-based path. This keeps
the app fully runnable as a demo even with zero API keys configured, while
still showing a genuine LLM-based path when keys are available.

Multimodal (image) classification uses Gemini specifically, since it's the
provider with vision support wired in here.
"""

import os
import json

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_MODEL_CANDIDATES = (
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)
LAST_GEMINI_ERROR = None


def get_last_gemini_error():
    return LAST_GEMINI_ERROR


def _generate_with_gemini(prompt: str, image=None):
    global LAST_GEMINI_ERROR
    LAST_GEMINI_ERROR = None
    if not GOOGLE_API_KEY:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)

        last_error = None
        for model_name in GEMINI_MODEL_CANDIDATES:
            try:
                model = genai.GenerativeModel(model_name)
                payload = [prompt, image] if image is not None else prompt
                response = model.generate_content(payload)
                if hasattr(response, "text") and response.text:
                    LAST_GEMINI_ERROR = None
                    return response.text
                if hasattr(response, "parts") and response.parts:
                    text = "".join(getattr(part, "text", "") for part in response.parts if getattr(part, "text", ""))
                    if text:
                        LAST_GEMINI_ERROR = None
                        return text
            except Exception as exc:  # pragma: no cover - defensive branch for runtime API errors
                last_error = exc
                LAST_GEMINI_ERROR = exc

        if last_error is not None:
            raise last_error
        return None
    except Exception as exc:
        LAST_GEMINI_ERROR = exc
        return None


def _try_gemini(prompt: str):
    return _generate_with_gemini(prompt)


def _try_gemini_vision(prompt: str, image):
    return _generate_with_gemini(prompt, image=image)


def _try_groq(prompt: str):
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def get_llm_response(prompt: str):
    """Return raw text from whichever provider is configured, or None."""
    text = _try_gemini(prompt)
    if text:
        return text
    text = _try_groq(prompt)
    if text:
        return text
    return None


def _parse_json(text: str):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned.strip())
    except Exception:
        return None


def get_llm_json(prompt: str):
    """Ask the LLM for strict JSON and parse it. Returns dict or None."""
    return _parse_json(get_llm_response(prompt))


def get_llm_json_multimodal(prompt: str, image):
    """Ask Gemini to classify an image (+ prompt) and return parsed JSON, or None."""
    text = _try_gemini_vision(prompt, image)
    return _parse_json(text)


def llm_is_configured() -> bool:
    return bool(GOOGLE_API_KEY or GROQ_API_KEY)
