import os
from dotenv import load_dotenv
from parsers.intent_parser import IntentParser
from tools.flight_search import search_flights, filter_by_airline
from tools.iata_lookup import city_to_iata
from agent.state import TravelAgentState

load_dotenv()
_parser = IntentParser()


def intent_parser_node(state: TravelAgentState) -> dict:
    """Parse user intent. Skips LLM if form data already populated."""
    already_populated = (
        state.get("origin_iata")
        and state.get("destination_iata")
        and state.get("depart_date")
    )
    if already_populated:
        # Return existing values unchanged — LangGraph requires at least one field written
        return {
            "origin_city": state.get("origin_city"),
            "origin_iata": state.get("origin_iata"),
            "destination_city": state.get("destination_city"),
            "destination_iata": state.get("destination_iata"),
            "depart_date": state.get("depart_date"),
            "return_date": state.get("return_date"),
            "budget_inr": state.get("budget_inr"),
            "num_adults": state.get("num_adults", 1),
            "num_children": state.get("num_children", 0),
            "trip_type": state.get("trip_type"),
            "special_requests": state.get("special_requests"),
            "preferred_airline": state.get("preferred_airline"),
        }

    messages = state.get("messages", [])
    if not messages:
        return {"error_message": "No user message found in state."}

    last_message = messages[-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    intent = _parser.parse(user_text)

    origin_iata = intent.origin_iata or city_to_iata(intent.origin_city or "")
    destination_iata = intent.destination_iata or city_to_iata(intent.destination_city or "")

    # Auto-populate default departure date if missing in NLP search
    depart_date = intent.departure_date
    if not depart_date:
        from datetime import date, timedelta
        depart_date = (date.today() + timedelta(days=14)).isoformat()

    return {
        "origin_city": intent.origin_city,
        "origin_iata": origin_iata,
        "destination_city": intent.destination_city,
        "destination_iata": destination_iata,
        "depart_date": depart_date,
        "return_date": intent.return_date,
        "budget_inr": intent.budget_inr,
        "num_adults": intent.num_adults or 1,
        "num_children": intent.num_children or 0,
        "trip_type": intent.trip_type,
        "special_requests": intent.special_requests,
        "preferred_airline": intent.preferred_airline,
    }


def validate_intent_node(state: TravelAgentState) -> dict:
    from datetime import date
    missing = []

    if not state.get("origin_iata"):
        missing.append("origin city (couldn't find IATA code)")
    if not state.get("destination_iata"):
        missing.append("destination city (couldn't find IATA code)")
    if not state.get("depart_date"):
        missing.append("departure date")
    else:
        try:
            parsed = date.fromisoformat(state["depart_date"])
            if parsed < date.today():
                missing.append(
                    f"departure date {state['depart_date']} is in the past — "
                    "please choose a future date"
                )
        except ValueError:
            missing.append("departure date format is invalid (expected YYYY-MM-DD)")

    return {"missing_fields": missing}


def flight_search_node(state: TravelAgentState) -> dict:
    origin_iata = state.get("origin_iata", "")
    destination_iata = state.get("destination_iata", "")
    depart_date = state.get("depart_date", "")
    return_date = state.get("return_date")
    num_adults = state.get("num_adults", 1)
    preferred_airline = state.get("preferred_airline")

    outbound = search_flights(
        dep_iata=origin_iata,
        arr_iata=destination_iata,
        flight_date=depart_date,
        return_date=return_date,
        adults=num_adults,
    )

    if preferred_airline:
        outbound = filter_by_airline(outbound, preferred_airline)

    return {
        "outbound_flights": outbound,
        "return_flights": [],
    }


def response_formatter_node(state: TravelAgentState) -> dict:
    # LangGraph requires at least one field written — pass error_message through
    return {"error_message": state.get("error_message")}