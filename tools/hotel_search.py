import os
import re                           # re = used to extract numbers from strings like "₹3,200"
from dotenv import load_dotenv

load_dotenv() 


def search_hotels(city_name: str,check_in_date: str,check_out_date: str,
adults: int = 1,children: int = 0,num_rooms: int = 1,) -> list[dict]:
    """
    Search for hotels using SerpApi's Google Hotels engine.
    Returns a list of hotel dicts, or an empty list [] if nothing found.
    
    Note: We already have the 'google-search-results' package installed
    for flights — the same package works for hotels too. No new install needed.
    """

    # Get the SerpApi key from .env
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        import logging
        logging.getLogger(__name__).warning("SERPAPI_KEY not found in environment. Falling back to default key.")
        api_key = "c4246b53f24b62686ce72487e23845342f3ec25dc691fa6e8057c672d959ddce"

    # Import the SerpApi library
    from serpapi import GoogleSearch

    # Build the search parameters.
    params = {
        "engine": "google_hotels",       # tell SerpApi to use Google Hotels
        "q": f"hotels in {city_name}",   # search query e.g. "hotels in Goa"
        "check_in_date": check_in_date,  # e.g. "2025-06-14"
        "check_out_date": check_out_date,# e.g. "2025-06-16"
        "adults": adults,
        "children": children,
        "rooms": num_rooms,
        "currency": "INR",               # show prices in Indian Rupees
        "hl": "en",                      # language = English
        "gl": "in",                      # country = India
        "api_key": api_key,
    }

    # Call the SerpApi and get results
    try:
        search = GoogleSearch(params)
        results = search.get_dict()      # returns a Python dictionary
    except Exception as e:
        raise RuntimeError(f"SerpApi connection failed: {e}")

    # Self-healing retry with fallback key if the configured key is invalid or exhausted
    fallback_key = "c4246b53f24b62686ce72487e23845342f3ec25dc691fa6e8057c672d959ddce"
    if "error" in results and api_key != fallback_key:
        err_msg = results["error"]
        if "Invalid API key" in err_msg or "exhausted" in err_msg or "out of searches" in err_msg or "limit" in err_msg.lower():
            params["api_key"] = fallback_key
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
            except Exception as e:
                raise RuntimeError(f"SerpApi connection failed on fallback: {e}")

    # Check if SerpApi returned an error message
    if "error" in results:
        raise ValueError(f"SerpApi error: {results['error']}")

    google_url = results.get("search_metadata", {}).get("google_url", "https://www.google.com/travel/hotels")
    # SerpApi stores hotel results under "properties" key
    raw_hotels = results.get("properties", [])

    # Clean each hotel result and return the list
    clean_hotels = []
    for h in raw_hotels:
        cleaned = _clean_hotel(h)
        cleaned["google_search_url"] = google_url
        clean_hotels.append(cleaned)
    return clean_hotels


def _clean_hotel(raw: dict) -> dict:
    """
    SerpApi returns messy hotel data with many nested fields.
    This function picks only the fields we need and flattens them.
    
    Input:  raw SerpApi hotel dict (many nested fields)
    Output: clean flat dict with only the fields our app uses
    """

    # Price comes as {"lowest": "₹3,200"} — we need to extract just the number 3200
    rate_info = raw.get("rate_per_night", {})
    price_str = rate_info.get("lowest", "") or rate_info.get("before_taxes_fees", "")
    price_inr = _extract_price_number(price_str)

    return {
        "hotel_name":       raw.get("name", "Unknown Hotel"),
        "hotel_id":         raw.get("property_token", ""),       # unique ID from Google
        "address":          raw.get("description", ""),
        "rating":           raw.get("overall_rating"),            # e.g. 4.3
        "reviews_count":    raw.get("reviews"),                   # e.g. 1240
        "hotel_class":      raw.get("hotel_class", ""),           # e.g. "3-star hotel"
        "price_per_night_inr": price_inr,                        # e.g. 3200
        "check_in_time":    raw.get("check_in_time", ""),         # e.g. "2:00 PM"
        "check_out_time":   raw.get("check_out_time", ""),        # e.g. "12:00 PM"
        "amenities":        raw.get("amenities", []),             # e.g. ["Pool", "WiFi", "Gym"]
        "images":           [                                     # take only first 3 images
            img.get("thumbnail", "")
            for img in raw.get("images", [])[:3]
        ],
        "nearby_places":    [                                     # take only first 3 nearby spots
            place.get("name", "")
            for place in raw.get("nearby_places", [])[:3]
        ],
        "booking_link":     raw.get("link", ""),                  # direct booking URL
        "serpapi_property_details_link": raw.get("property_details_link", ""),  # SerpApi's hotel details page
    }


def _extract_price_number(price_str: str) -> int | None:
    """
    Convert a price string like "₹3,200" or "INR 3200" into just the number 3200.
    Returns None if no number found.
    
    Examples:
        "₹3,200"   → 3200
        "INR 5000" → 5000
        ""         → None
    """
    if not price_str:
        return None

    # Remove currency symbols and commas, then find the first number
    cleaned = price_str.replace("₹", "").replace("INR", "").replace(",", "").strip()
    match = re.search(r"\d+", cleaned)

    return int(match.group()) if match else None


def filter_hotels_by_budget(hotels: list[dict], max_budget_inr: int) -> list[dict]:
    """
    Keep only hotels that cost less than or equal to max_budget_inr per night.
    
    If NO hotel fits the budget (all are too expensive),
    we return the full list anyway — better to show something than nothing.
    
    Example:
        hotels = [{price: 2000}, {price: 4000}, {price: 6000}]
        max_budget_inr = 5000
        → returns [{price: 2000}, {price: 4000}]
    """
    if not max_budget_inr or not hotels:
        return hotels   # nothing to filter, return as-is

    within_budget = [
        hotel for hotel in hotels
        if hotel.get("price_per_night_inr") is not None          # skip hotels with no price
        and hotel["price_per_night_inr"] <= max_budget_inr       # only within budget
    ]

    # If nothing is within budget, return full list (fallback)
    return within_budget if within_budget else hotels