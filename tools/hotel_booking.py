# tools/hotel_booking.py
# ─────────────────────────────────────────────────────────────────────────────
# This file builds booking URLs for 3 platforms:
#   1. Booking.com
#   2. MakeMyTrip
#   3. Expedia
#
# Each URL is pre-filled with:
#   - Hotel name / city
#   - Check-in & check-out dates
#   - Number of guests & rooms
#
# When user clicks "View Deal" on a hotel card, the frontend shows a popup
# with 3 buttons — one for each platform. Each button opens the URL built here.
# ─────────────────────────────────────────────────────────────────────────────

from urllib.parse import urlencode, quote_plus
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Date format converters
# ─────────────────────────────────────────────────────────────────────────────

def _to_mmddyyyy(date_str: str) -> str:
    """
    Convert YYYY-MM-DD → MM/DD/YYYY
    Required by Expedia URLs.
    
    Example: "2026-06-20" → "06/20/2026"
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%m/%d/%Y")
    except Exception:
        return date_str


def _to_mmdddyyyy_mmt(date_str: str) -> str:
    """
    Convert YYYY-MM-DD → MMDDYYYY (no slashes)
    Required by MakeMyTrip URLs.

    Example: "2026-06-20" → "06202026"
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%m%d%Y")
    except Exception:
        return date_str


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM 1 — Booking.com
# ─────────────────────────────────────────────────────────────────────────────

def build_booking_com_url(
    hotel_name:    str,
    city:          str,
    check_in:      str,   # YYYY-MM-DD
    check_out:     str,   # YYYY-MM-DD
    num_adults:    int = 1,
    num_children:  int = 0,
    num_rooms:     int = 1,
) -> str:
    """
    Build a Booking.com search URL pre-filled with hotel and stay details.

    Booking.com URL format:
        https://www.booking.com/searchresults.html
            ?ss=<hotel+name+city>
            &checkin=YYYY-MM-DD
            &checkout=YYYY-MM-DD
            &group_adults=<adults>
            &group_children=<children>
            &no_rooms=<rooms>
            &nflt=class%3D<stars>   (optional star filter)

    Example output:
        https://www.booking.com/searchresults.html?ss=Taj+Hotel+Mumbai&checkin=2026-06-20&checkout=2026-06-22&group_adults=2&group_children=0&no_rooms=1
    """
    # Combine hotel name + city for best search match
    search_query = f"{hotel_name} {city}".strip()

    params = {
        "ss":              search_query,
        "checkin":         check_in,
        "checkout":        check_out,
        "group_adults":    num_adults,
        "group_children":  num_children,
        "no_rooms":        num_rooms,
        "lang":            "en-us",
        "selected_currency": "INR",
    }

    return f"https://www.booking.com/searchresults.html?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM 2 — MakeMyTrip
# ─────────────────────────────────────────────────────────────────────────────

def build_makemytrip_url(
    city:          str,
    check_in:      str,   # YYYY-MM-DD
    check_out:     str,   # YYYY-MM-DD
    num_adults:    int = 1,
    num_rooms:     int = 1,
) -> str:
    """
    Build a MakeMyTrip hotel search URL pre-filled with stay details.

    MakeMyTrip URL format:
        https://www.makemytrip.com/hotels/hotel-listing/
            ?city=<city>
            &checkin=MMDDYYYY
            &checkout=MMDDYYYY
            &roomStayQualifier=<adults>e0e   (e.g. "2e0e" = 2 adults, 0 children)
            &locusId=CITY<IATA>              (optional, improves accuracy)
            &country=IN

    roomStayQualifier format: "<adults>e<children>e" per room
    Example: 2 adults, 0 children, 1 room → "2e0e"
             2 adults, 0 children, 2 rooms → "2e0e2e0e"

    Example output:
        https://www.makemytrip.com/hotels/hotel-listing/?city=Mumbai&checkin=06202026&checkout=06222026&roomStayQualifier=2e0e&country=IN
    """
    # Build roomStayQualifier — repeat per room
    room_qualifier = "".join([f"{num_adults}e0e"] * num_rooms)

    params = {
        "city":               city,
        "checkin":            _to_mmdddyyyy_mmt(check_in),
        "checkout":           _to_mmdddyyyy_mmt(check_out),
        "roomStayQualifier":  room_qualifier,
        "country":            "IN",
    }

    return f"https://www.makemytrip.com/hotels/hotel-listing/?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM 3 — Expedia
# ─────────────────────────────────────────────────────────────────────────────

def build_expedia_url(
    hotel_name:    str,
    city:          str,
    check_in:      str,   # YYYY-MM-DD
    check_out:     str,   # YYYY-MM-DD
    num_adults:    int = 1,
    num_rooms:     int = 1,
) -> str:
    """
    Build an Expedia hotel search URL pre-filled with stay details.

    Expedia URL format:
        https://www.expedia.co.in/Hotel-Search
            ?destination=<hotel+name+city>
            &startDate=MM/DD/YYYY
            &endDate=MM/DD/YYYY
            &adults=<adults>
            &rooms=<rooms>

    Example output:
        https://www.expedia.co.in/Hotel-Search?destination=Taj+Hotel+Mumbai&startDate=06/20/2026&endDate=06/22/2026&adults=2&rooms=1
    """
    # Combine hotel name + city for best search match
    search_query = f"{hotel_name} {city}".strip()

    params = {
        "destination": search_query,
        "startDate":   _to_mmddyyyy(check_in),
        "endDate":     _to_mmddyyyy(check_out),
        "adults":      num_adults,
        "rooms":       num_rooms,
    }

    return f"https://www.expedia.co.in/Hotel-Search?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION — Build all 3 booking URLs for a hotel
# ─────────────────────────────────────────────────────────────────────────────

def build_hotel_booking_urls(
    hotel_name:    str,
    city:          str,
    check_in:      str,   # YYYY-MM-DD
    check_out:     str,   # YYYY-MM-DD
    num_adults:    int = 1,
    num_children:  int = 0,
    num_rooms:     int = 1,
) -> dict:
    """
    Build all 3 booking URLs for a single hotel.
    This is the main function called from run.py for each hotel in the results.

    Returns a dict with 3 URLs:
    {
        "booking_com":   "https://www.booking.com/searchresults.html?...",
        "makemytrip":    "https://www.makemytrip.com/hotels/hotel-listing/?...",
        "expedia":       "https://www.expedia.co.in/Hotel-Search?...",
    }

    These 3 URLs are added to each hotel in the API response.
    The frontend shows them as 3 buttons in the "View Deal" popup.
    """
    return {
        "booking_com": build_booking_com_url(
            hotel_name=   hotel_name,
            city=         city,
            check_in=     check_in,
            check_out=    check_out,
            num_adults=   num_adults,
            num_children= num_children,
            num_rooms=    num_rooms,
        ),
        "makemytrip": build_makemytrip_url(
            city=         city,
            check_in=     check_in,
            check_out=    check_out,
            num_adults=   num_adults,
            num_rooms=    num_rooms,
        ),
        "expedia": build_expedia_url(
            hotel_name=   hotel_name,
            city=         city,
            check_in=     check_in,
            check_out=    check_out,
            num_adults=   num_adults,
            num_rooms=    num_rooms,
        ),
    }