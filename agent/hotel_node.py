import os
from dotenv import load_dotenv
from parsers.hotel_intent_parser import HotelIntentParser
from tools.hotel_search import search_hotels, filter_hotels_by_budget
from tools.hotel_booking import build_hotel_booking_urls
from agent.hotel_state import HotelAgentState

load_dotenv()
_hotel_parser = HotelIntentParser()

# Maps IATA city codes back to readable city name for the hotel search query
IATA_TO_CITY = {
    "DEL": "Delhi", "BOM": "Mumbai", "BLR": "Bengaluru", "AMD": "Ahmedabad",
    "GOI": "Goa", "CCU": "Kolkata", "MAA": "Chennai", "HYD": "Hyderabad",
    "PNQ": "Pune", "JAI": "Jaipur", "COK": "Kochi", "LKO": "Lucknow",
    "BDQ": "Vadodara", "IXC": "Chandigarh", "DXB": "Dubai",
    "SIN": "Singapore", "LHR": "London", "BKK": "Bangkok",
}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1 — Parse what the user wants
# ─────────────────────────────────────────────────────────────────────────────

def hotel_intent_parser_node(state: HotelAgentState) -> dict:
    """
    Two cases:
    
    CASE A — User came from the FORM (city/dates already filled in):
        Skip the AI call. Just return the existing values unchanged.
        (The form already gave us structured data, no need to parse anything)
    
    CASE B — User typed a natural language message:
        Send the message to Groq AI → AI fills in a HotelIntent form → return the values.
    """

    # CASE A: Check if the key fields are already in the state (came from form)
    form_data_present = (
        state.get("city")
        and state.get("check_in_date")
        and state.get("check_out_date")
    )

    if form_data_present:
        # Form data is already there — just pass it through unchanged
        # (LangGraph requires us to return at least one field, so we return all of them)
        return {
            "city":                 state.get("city"),
            "city_iata":            state.get("city_iata"),
            "check_in_date":        state.get("check_in_date"),
            "check_out_date":       state.get("check_out_date"),
            "num_adults":           state.get("num_adults", 1),
            "num_children":         state.get("num_children", 0),
            "num_rooms":            state.get("num_rooms", 1),
            "budget_per_night_inr": state.get("budget_per_night_inr"),
            "hotel_type":           state.get("hotel_type"),
            "amenities":            state.get("amenities"),
            "trip_type":            state.get("trip_type"),
            "special_requests":     state.get("special_requests"),
        }

    # CASE B: Get the last message the user typed
    messages = state.get("messages", [])
    # message = state["messages"]
    if not messages:
        return {"error_message": "No user message found."}

    last_message = messages[-1]

    # Extract the text — message objects have a .content attribute
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    # Send to AI → get back a filled HotelIntent object
    intent = _hotel_parser.parse(user_text)

    # If AI gave us an IATA code but no city name, look up the city name
    city = intent.city
    if not city and intent.city_iata:
        city = IATA_TO_CITY.get(intent.city_iata.upper(), intent.city_iata)

    # Auto-populate default check-in/out dates if they are missing in NLP search
    check_in = intent.check_in_date
    check_out = intent.check_out_date
    from datetime import date, timedelta
    if not check_in:
        check_in = (date.today() + timedelta(days=7)).isoformat()
    if not check_out:
        check_out = (date.fromisoformat(check_in) + timedelta(days=3)).isoformat()

    # Return all the parsed values to update the state
    return {
        "city":                 city,
        "city_iata":            intent.city_iata,
        "check_in_date":        check_in,
        "check_out_date":       check_out,
        "num_adults":           intent.num_adults or 1,
        "num_children":         intent.num_children or 0,
        "num_rooms":            intent.num_rooms or 1,
        "budget_per_night_inr": intent.budget_per_night_inr,
        "hotel_type":           intent.hotel_type,
        "amenities":            intent.amenities,
        "trip_type":            intent.trip_type,
        "special_requests":     intent.special_requests,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2 — Check if we have everything we need to search
# ─────────────────────────────────────────────────────────────────────────────

def hotel_validate_intent_node(state: HotelAgentState) -> dict:
    """
    Check if the 3 required fields are present and valid:
        1. city          — must not be empty
        2. check_in_date — must exist and be a future date
        3. check_out_date — must exist and be after check_in_date
    
    Any problems are added to the missing_fields list.
    If missing_fields is empty → hotel_search_node runs next.
    If missing_fields has items → hotel_response_formatter_node runs next (skip search).
    """
    from datetime import date

    missing = []  # list to collect any problems we find

    # Check 1: city must be provided
    if not state.get("city"):
        missing.append("city name")

    # Check 2: check-in date must exist and be a future date
    check_in = state.get("check_in_date")
    if not check_in:
        missing.append("check-in date")
    else:
        try:
            check_in_date = date.fromisoformat(check_in)   # convert "2025-06-14" to a date object
            if check_in_date < date.today():
                missing.append(f"check-in date {check_in} is in the past — please pick a future date")
        except ValueError:
            missing.append("check-in date must be in YYYY-MM-DD format")

    # Check 3: check-out date must exist and be after check-in
    check_out = state.get("check_out_date")
    if not check_out:
        missing.append("check-out date")
    else:
        try:
            check_out_date = date.fromisoformat(check_out)
            if check_in:                                        # only compare if check-in is valid
                try:
                    if check_out_date <= date.fromisoformat(check_in):
                        missing.append("check-out date must be after check-in date")
                except ValueError:
                    pass  # check-in format error already caught above
        except ValueError:
            missing.append("check-out date must be in YYYY-MM-DD format")

    # Return the list of problems (empty list = everything is fine)
    return {"missing_fields": missing}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3 — Search for hotels (only runs if validation passed)
# ─────────────────────────────────────────────────────────────────────────────

def hotel_search_node(state: HotelAgentState) -> dict:
    """
    Call SerpApi to search for hotels using the data in state.
    If user gave a budget, filter results to only show affordable options.
    """

    # Read all search parameters from the state
    city       = state.get("city", "")
    check_in   = state.get("check_in_date", "")
    check_out  = state.get("check_out_date", "")
    adults     = state.get("num_adults", 1)
    children   = state.get("num_children", 0)
    rooms      = state.get("num_rooms", 1)
    budget     = state.get("budget_per_night_inr")   # None if user didn't mention budget

    # Search for hotels via SerpApi Google Hotels
    hotels = search_hotels(
        city_name=city,
        check_in_date=check_in,
        check_out_date=check_out,
        adults=adults,
        children=children,
        num_rooms=rooms,
    )

    # If user mentioned a budget, filter out hotels that are too expensive
    if budget:
        hotels = filter_hotels_by_budget(hotels, budget)

    for hotel in hotels:
        hotel["check_in_date"] = check_in
        hotel["check_out_date"] = check_out
        hotel["booking_links"] = build_hotel_booking_urls(
            hotel_name=hotel.get("hotel_name", ""),
            city=city,
            check_in=check_in,
            check_out=check_out,
            num_adults=adults,
            num_children=children,
            num_rooms=rooms,
        )
    
    # Save results to state
    return {"hotels": hotels}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 — Final step before sending response to the API
# ─────────────────────────────────────────────────────────────────────────────

def hotel_response_formatter_node(state: HotelAgentState) -> dict:
    """
    This node is the last step for BOTH paths (search success AND abort).
    
    Its only job: pass the error_message through to the state.
    LangGraph requires every node to write at least one field — this is why this node exists.
    
    The actual response building (converting state → JSON) happens in hotel_service.py.
    """
    return {"error_message": state.get("error_message")}