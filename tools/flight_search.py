import os
from dotenv import load_dotenv

load_dotenv()


def search_flights(
    dep_iata: str,
    arr_iata: str,
    flight_date: str,
    return_date: str = None,
    adults: int = 1,
) -> list[dict]:
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise ValueError(
            "SERPAPI_KEY not found in .env.\n"
            "Sign up free at https://serpapi.com/users/sign_up"
        )

    try:
        from serpapi import GoogleSearch
    except ImportError:
        raise ImportError("Install serpapi: pip install google-search-results")

    params = {
        "engine": "google_flights",
        "departure_id": dep_iata.upper(),
        "arrival_id": arr_iata.upper(),
        "outbound_date": flight_date,
        "currency": "INR",
        "hl": "en",
        "gl": "in",
        "adults": adults,
        "api_key": api_key,
        "deep_search": True,
        "type": "1" if return_date else "2",
    }
    if return_date:
        params["return_date"] = return_date

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        print(f"[SerpApi Error] {e}")
        return []

    if "error" in results:
        print(f"[SerpApi Error] {results['error']}")
        return []

    raw_flights = results.get("best_flights", []) + results.get("other_flights", [])
    return [_clean_flight(f) for f in raw_flights] if raw_flights else []


def _clean_flight(raw: dict) -> dict:
    legs = raw.get("flights", [])
    first_leg = legs[0] if legs else {}
    last_leg = legs[-1] if legs else {}

    dep_airport = first_leg.get("departure_airport", {})
    arr_airport = last_leg.get("arrival_airport", {})
    airlines = list({leg.get("airline", "") for leg in legs if leg.get("airline")})
    flight_numbers = [leg.get("flight_number", "") for leg in legs if leg.get("flight_number")]

    return {
        "flight_number": ", ".join(flight_numbers) or "N/A",
        "airline": ", ".join(airlines) or "Unknown",
        "departure_airport": dep_airport.get("name", ""),
        "departure_iata": dep_airport.get("id", ""),
        "departure_time": dep_airport.get("time", ""),
        "arrival_airport": arr_airport.get("name", ""),
        "arrival_iata": arr_airport.get("id", ""),
        "arrival_time": arr_airport.get("time", ""),
        "duration_minutes": raw.get("total_duration", 0),
        "stops": len(legs) - 1,
        "price_inr": raw.get("price"),
        "travel_class": first_leg.get("travel_class", "Economy"),
        "flight_status": "scheduled",
        "flight_date": first_leg.get("departure_airport", {}).get("time", "")[:10] if legs else "",
        "layovers": raw.get("layovers", []),
    }


AIRLINE_ALIASES: dict[str, list[str]] = {
    "indigo": ["indigo", "6e"],
    "air india": ["air india", "ai"],
    "spicejet": ["spicejet", "sg"],
    "vistara": ["vistara", "uk"],
    "akasa": ["akasa", "qp"],
}


def filter_by_airline(flights: list[dict], preferred_airline: str) -> list[dict]:
    if not preferred_airline or not flights:
        return flights

    search_term = preferred_airline.lower().strip()
    match_terms = [search_term]

    for canonical, aliases in AIRLINE_ALIASES.items():
        if search_term in canonical or canonical in search_term:
            match_terms.extend(aliases)
            break
        if any(search_term in alias or alias in search_term for alias in aliases):
            match_terms.extend(aliases)
            break

    filtered = [
        f for f in flights
        if any(
            term in f.get("airline", "").lower() or
            term in f.get("flight_number", "").lower()
            for term in match_terms
        )
    ]
    return filtered if filtered else flights
