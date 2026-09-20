"""
Location search utility for civic complaint system.

Provides location autocomplete using local ward dataset.
For production use with Google Maps, set GOOGLE_PLACES_API_KEY in .env.
"""

import os
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Google Places API (optional - for production with Google Maps)
# Note: Google Places API is a paid service with $200/month credit
# For demo/development, local dataset fallback is used automatically
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def get_place_autocomplete(search_text: str, city: str = None, city_wards=None) -> list:
    """
    Get location suggestions from local ward dataset.

    Args:
        search_text: User's search input
        city: City to filter results (optional)
        city_wards: DataFrame with city/ward data for filtering (optional)

    Returns:
        List of place suggestions with descriptions

    Note: For production use with Google Maps Places API, set
    GOOGLE_PLACES_API_KEY in .env file. This key is paid (not free).
    """
    if not search_text or len(search_text) < 1:
        return []

    # Try Google Places API if key is configured (optional, paid service)
    if GOOGLE_PLACES_API_KEY:
        try:
            import requests
            url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
            params = {
                "input": search_text,
                "key": GOOGLE_PLACES_API_KEY,
                "components": "country:in",
                "language": "en",
            }
            response = requests.get(url, params=params, timeout=3)
            data = response.json()
            if data.get("status") == "OK" and data.get("predictions"):
                suggestions = []
                for pred in data["predictions"][:8]:
                    suggestions.append({
                        "description": pred.get("description", ""),
                        "place_id": pred.get("place_id", ""),
                        "main_text": pred.get("structured_formatting", {}).get("main_text", ""),
                        "secondary_text": pred.get("structured_formatting", {}).get("secondary_text", ""),
                        "source": "google_places"
                    })
                return suggestions
        except Exception:
            pass  # Fall back to local dataset

    # Default: Use local dataset fallback (free, always available)
    if city_wards is not None:
        try:
            import pandas as pd
            wards_in_city = city_wards[city_wards["city"] == city]["ward"].unique() if city else city_wards["ward"].unique()
            filtered_wards = [
                w for w in sorted(wards_in_city)
                if search_text.lower() in w.lower()
            ]

            if filtered_wards:
                return [
                    {
                        "description": f"{w}, {city}" if city else w,
                        "place_id": "",
                        "main_text": w,
                        "secondary_text": city if city else "",
                        "source": "local_dataset"
                    }
                    for w in filtered_wards
                ]
        except Exception:
            pass

    return []


def get_place_details(place_id: str) -> dict:
    """
    Get detailed information about a place using Google Places API.

    Args:
        place_id: Google Place ID

    Returns:
        Place details including coordinates

    Note: Requires GOOGLE_PLACES_API_KEY (paid Google service).
    """
    if not GOOGLE_PLACES_API_KEY or not place_id:
        return {}

    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": GOOGLE_PLACES_API_KEY,
            "fields": "geometry,formatted_address",
        }
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        if data.get("result"):
            result = data["result"]
            return {
                "formatted_address": result.get("formatted_address", ""),
                "latitude": result.get("geometry", {}).get("location", {}).get("lat"),
                "longitude": result.get("geometry", {}).get("location", {}).get("lng"),
            }
    except Exception:
        pass

    return {}


