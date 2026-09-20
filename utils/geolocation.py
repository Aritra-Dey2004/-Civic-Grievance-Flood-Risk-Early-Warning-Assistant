"""
Geolocation helper for automatic city/ward detection.

Uses IP-based geolocation to detect user's approximate location and
maps it to the nearest supported city and ward in the system.
"""

import requests
import streamlit as st
from utils.data_loader import load_complaints

# Approximate city coordinates (latitude, longitude) for Indian cities
CITY_COORDS = {
    "Kolkata": (22.5726, 88.3639),
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.7041, 77.1025),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Guwahati": (26.1445, 91.7362),
}

# Ward coordinates within each city (approximate central locations)
WARD_COORDS = {
    "Kolkata": {
        "Ward 33 - Park Circus": (22.5520, 88.3730),
        "Ward 12 - Ballyganj": (22.5380, 88.3650),
        "Ward 45 - Tangra": (22.5650, 88.3920),
        "Ward 78 - Tollyganj": (22.5150, 88.3500),
        "Girih Park": (22.5600, 88.3650),
    },
    "Mumbai": {
        "Ward A - South Mumbai": (19.0176, 72.8194),
        "Ward B - Central Mumbai": (19.0260, 72.8235),
        "Ward C - North Mumbai": (19.1136, 72.8697),
        "Ward D - Eastern Mumbai": (19.0881, 72.9454),
    },
    "Delhi": {
        "Ward 1 - Central Delhi": (28.6329, 77.2197),
        "Ward 2 - East Delhi": (28.5921, 77.2747),
        "Ward 3 - South Delhi": (28.5244, 77.1855),
        "Ward 4 - North Delhi": (28.7405, 77.2273),
    },
    "Bengaluru": {
        "Ward 1 - Whitefield": (12.9698, 77.7499),
        "Ward 2 - Koramangala": (12.9352, 77.6245),
        "Ward 3 - Indiranagar": (12.9716, 77.6412),
        "Ward 4 - Jayanagar": (12.9352, 77.5945),
    },
    "Chennai": {
        "Ward 1 - George Town": (13.1613, 80.2855),
        "Ward 2 - T. Nagar": (13.0348, 80.2370),
        "Ward 3 - Adyar": (13.0011, 80.2405),
        "Ward 4 - Besant Nagar": (13.0033, 80.2610),
    },
    "Hyderabad": {
        "Ward 1 - Secunderabad": (17.3686, 78.4942),
        "Ward 2 - Begumpet": (17.3758, 78.4728),
        "Ward 3 - Madhapur": (17.4406, 78.4486),
        "Ward 4 - Kukatpally": (17.4601, 78.4272),
    },
    "Pune": {
        "Ward 1 - Koregaon Park": (18.5283, 73.8551),
        "Ward 2 - Viman Nagar": (18.5614, 73.9128),
        "Ward 3 - Camp": (18.5314, 73.8722),
        "Ward 4 - Kothrud": (18.5087, 73.8338),
    },
    "Guwahati": {
        "Ward 1 - Pan Bazaar": (26.1781, 91.7364),
        "Ward 2 - Ulubari": (26.1913, 91.7470),
        "Ward 3 - Bhangagarh": (26.1567, 91.7267),
        "Ward 4 - Paltan Bazaar": (26.1745, 91.7450),
    },
}


def get_user_location():
    """
    Fetch user's approximate location using IP geolocation.
    Returns (latitude, longitude) or None if detection fails.
    """
    try:
        # Try ipapi.co first
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat and lon:
                return float(lat), float(lon)
    except Exception:
        pass

    try:
        # Fallback to ip-api.com
        response = requests.get("http://ip-api.com/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                lat = data.get("lat")
                lon = data.get("lon")
                if lat and lon:
                    return float(lat), float(lon)
    except Exception:
        pass

    return None


def find_nearest_city(lat: float, lon: float) -> str:
    """
    Given user coordinates, find the nearest supported city.
    Returns city name or None if no close match found.
    """
    min_distance = float("inf")
    nearest_city = None

    for city, (city_lat, city_lon) in CITY_COORDS.items():
        # Simple Euclidean distance (good enough for Indian cities)
        distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_city = city

    # Only return if within reasonable distance (~200 km ≈ 2 degrees)
    if min_distance < 2:
        return nearest_city
    return None


def find_nearest_ward(city: str, lat: float, lon: float) -> str:
    """
    Given city and coordinates, find the nearest ward.
    Returns ward name or None if city not found.
    """
    if city not in WARD_COORDS:
        return None

    wards = WARD_COORDS[city]
    min_distance = float("inf")
    nearest_ward = None

    for ward, (ward_lat, ward_lon) in wards.items():
        # Distance to ward
        distance = ((lat - ward_lat) ** 2 + (lon - ward_lon) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_ward = ward

    return nearest_ward


def detect_and_set_location(city_wards_df):
    """
    Attempt to auto-detect user location (city AND ward) and set defaults in session state.
    Called once on app load.
    """
    if "detected_city" in st.session_state:
        return  # Already attempted detection

    user_location = get_user_location()
    if user_location:
        lat, lon = user_location
        detected_city = find_nearest_city(lat, lon)
        if detected_city:
            detected_ward = find_nearest_ward(detected_city, lat, lon)
            st.session_state["detected_city"] = detected_city
            st.session_state["detected_ward"] = detected_ward
            st.session_state["auto_detected"] = True
            return

    st.session_state["detected_city"] = None
    st.session_state["detected_ward"] = None
    st.session_state["auto_detected"] = False

