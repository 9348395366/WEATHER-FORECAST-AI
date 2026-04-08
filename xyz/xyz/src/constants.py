from __future__ import annotations

ODISHA_COORDS = (20.2961, 85.8245)
ODISHA_LABEL = "India - Odisha"

INDIA_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttarakhand",
    "Uttar Pradesh",
    "West Bengal",
]


ODISHA_DISTRICTS = [
    "Angul",
    "Boudh",
    "Balangir",
    "Bargarh",
    "Balasore (Baleswar)",
    "Bhadrak",
    "Cuttack",
    "Deogarh (Debagarh)",
    "Dhenkanal",
    "Ganjam",
    "Gajapati",
    "Jharsuguda",
    "Jajpur",
    "Jagatsinghapur",
    "Khordha",
    "Keonjhar (Kendujhar)",
    "Kalahandi",
    "Kandhamal",
    "Koraput",
    "Kendrapara",
    "Malkangiri",
    "Mayurbhanj",
    "Nabarangpur",
    "Nuapada",
    "Nayagarh",
    "Puri",
    "Rayagada",
    "Sambalpur",
    "Subarnapur (Sonepur)",
    "Sundargarh",
]


def _district_base(name: str) -> str:
    return name.split(" (", 1)[0]


LOCATIONS = {
    "Custom": None,
}

LOCATION_QUERIES = {}

for state in INDIA_STATES:
    label = f"India - {state}"
    LOCATIONS[label] = None
    LOCATION_QUERIES[label] = f"{state}, India"

for district in ODISHA_DISTRICTS:
    label = f"Odisha - {district}"
    LOCATIONS[label] = None
    LOCATION_QUERIES[label] = f"{_district_base(district)}, Odisha, India"

NAV_LINKS = [
    ("Home", "app.py"),
    ("Live Weather", "pages/1_Live_Weather.py"),
    ("AI Forecast", "pages/2_AI_Forecast.py"),
    ("Data Lab", "pages/3_Data_Lab.py"),
    ("Agent Chat", "pages/4_Agent_Chat.py"),
    ("About", "pages/5_About.py"),
]

INDIA_BOUNDS = {
    "lat_min": 6.0,
    "lat_max": 37.5,
    "lon_min": 68.0,
    "lon_max": 97.5,
}


def is_in_india(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    try:
        lat_val = float(lat)
        lon_val = float(lon)
    except (TypeError, ValueError):
        return False
    return (
        INDIA_BOUNDS["lat_min"] <= lat_val <= INDIA_BOUNDS["lat_max"]
        and INDIA_BOUNDS["lon_min"] <= lon_val <= INDIA_BOUNDS["lon_max"]
    )


def timezone_for_location(lat: float | None, lon: float | None) -> str:
    return "Asia/Kolkata" if is_in_india(lat, lon) else "auto"

