# This file is the bridge between the API routes and the LangGraph agent.
# It prepares the initial state, runs the graph, and converts the result to a response.
#
# Two public functions:
#   search_hotels_nlp()  → for natural language searches ("hotels in Goa next Friday")
#   search_hotels_form() → for structured form searches (city/dates already selected)

import logging
from typing import Optional
from langchain_core.messages import HumanMessage    # wraps user text as a message object

from models.api_models import HotelSearchResponse, HotelResult, HotelSearchMetadata

logger = logging.getLogger(__name__)

# Try to create the intent parser at startup
# If GROQ_API_KEY is missing, we store None and show a clear error when NLP is called
try:
    from parsers.hotel_intent_parser import HotelIntentParser
    _hotel_intent_parser = HotelIntentParser()
except ValueError as exc:
    _hotel_intent_parser = None
    logger.warning("HotelIntentParser could not start: %s", exc)


def _build_initial_state(form_data: dict) -> dict:
    """
    Convert a flat form_data dict into the initial state dict that the LangGraph needs.
    
    The 'messages' field is required by LangGraph even for form searches.
    We create a simple summary message so the state is valid.
    
    Example input:
        form_data = {"city": "Goa", "check_in_date": "2025-06-14", ...}
    
    Example output:
        {
            "messages": [HumanMessage("Hotels in Goa from 2025-06-14 to 2025-06-16")],
            "city": "Goa",
            "check_in_date": "2025-06-14",
            ...
        }
    """
    return {
        # Create a summary message for the LangGraph messages field
        "messages": [HumanMessage(content=(
            f"Hotels in {form_data.get('city', '?')} "
            f"from {form_data.get('check_in_date', '?')} "
            f"to {form_data.get('check_out_date', '?')}"
        ))],

        # Copy all form fields into the state
        "city":                 form_data.get("city"),
        "city_iata":            form_data.get("city_iata"),
        "check_in_date":        form_data.get("check_in_date"),
        "check_out_date":       form_data.get("check_out_date"),
        "num_adults":           form_data.get("num_adults", 1),
        "num_children":         form_data.get("num_children", 0),
        "num_rooms":            form_data.get("num_rooms", 1),
        "budget_per_night_inr": form_data.get("budget_per_night_inr"),
        "hotel_type":           form_data.get("hotel_type"),
        "amenities":            form_data.get("amenities"),
        "trip_type":            form_data.get("trip_type"),
        "special_requests":     form_data.get("special_requests"),

        # These will be filled in by the agent nodes — start them empty
        "hotels":        [],
        "missing_fields": [],
        "error_message":  None,
    }


def _build_response(final_state: dict, request_id: Optional[str] = None) -> HotelSearchResponse:
    """
    After the LangGraph finishes running, convert the final state into a
    HotelSearchResponse object that FastAPI will send back to the frontend.
    
    Status logic:
        error_message is set    → status = "error"
        missing_fields not empty → status = "missing_fields"
        hotels list not empty   → status = "success"
        hotels list is empty    → status = "no_results"
    """

    error_msg = final_state.get("error_message")
    missing   = final_state.get("missing_fields", [])
    hotels    = final_state.get("hotels", [])

    # Decide the status code
    if error_msg:
        status = "error"
    elif missing:
        status = "missing_fields"
    elif hotels:
        status = "success"
    else:
        status = "no_results"

    # Convert raw hotel dicts to HotelResult Pydantic objects (for type validation)
    hotel_objects = [HotelResult(**h) for h in hotels if isinstance(h, dict)]

    # Human-readable message for each status
    status_messages = {
        "success":        "Hotels found successfully.",
        "no_results":     "No hotels found for this city and dates.",
        "missing_fields": "Search could not complete — some required fields are missing.",
        "error":          "Search failed due to an internal error.",
    }

    return HotelSearchResponse(
        status=status,
        message=status_messages.get(status, "Unknown status."),
        request_id=request_id,
        metadata=HotelSearchMetadata(
            city=final_state.get("city"),
            city_iata=final_state.get("city_iata"),
            check_in_date=final_state.get("check_in_date"),
            check_out_date=final_state.get("check_out_date"),
            num_adults=final_state.get("num_adults", 1),
            num_children=final_state.get("num_children", 0),
            num_rooms=final_state.get("num_rooms", 1),
            budget_per_night_inr=final_state.get("budget_per_night_inr"),
            hotel_type=final_state.get("hotel_type"),
            trip_type=final_state.get("trip_type"),
        ),
        hotels=hotel_objects,
        missing_fields=missing,
        error_detail=error_msg,
        hotel_count=len(hotel_objects),
    )


async def search_hotels_nlp(
    hotel_graph,
    message: str,
    request_id: Optional[str] = None,
) -> HotelSearchResponse:
    """
    Handle a natural language hotel search request.
    
    Example message: "I need a hotel in Goa for 2 nights next Friday under 3000"
    
    Steps:
        1. Parse the message with AI → get structured form_data
        2. Build initial state from form_data
        3. Run the LangGraph agent
        4. Convert final state to response
    """

    # If the AI parser wasn't initialised (missing API key), return error immediately
    if _hotel_intent_parser is None:
        return HotelSearchResponse(
            status="error",
            message="NLP search is not available — GROQ_API_KEY is not configured.",
            request_id=request_id,
            error_detail="GROQ_API_KEY missing",
            hotel_count=0,
        )

    try:
        logger.info("Hotel NLP search: %.80s", message)   # log first 80 chars of message

        # Step 1: Parse the natural language message into structured data
        intent = _hotel_intent_parser.parse(message)

        # Step 2: Convert intent object to a flat dict (same format as form data)
        form_data = {
            "city":                 intent.city,
            "city_iata":            intent.city_iata,
            "check_in_date":        intent.check_in_date,
            "check_out_date":       intent.check_out_date,
            "num_adults":           intent.num_adults,
            "num_children":         intent.num_children,
            "num_rooms":            intent.num_rooms,
            "budget_per_night_inr": intent.budget_per_night_inr,
            "hotel_type":           intent.hotel_type,
            "amenities":            intent.amenities,
            "trip_type":            intent.trip_type,
            "special_requests":     intent.special_requests,
        }

        # Step 3: Build initial state and run the graph
        initial_state = _build_initial_state(form_data)
        initial_state["messages"] = [HumanMessage(content=message)]
        final_state   = hotel_graph.invoke(initial_state)

        # Step 4: Build and return the response
        return _build_response(final_state, request_id=request_id)

    except Exception as exc:
        logger.exception("Hotel NLP search failed: %s", exc)
        return HotelSearchResponse(
            status="error",
            message=f"Hotel search failed: {str(exc)}",
            request_id=request_id,
            error_detail=str(exc),
            hotel_count=0,
        )


async def search_hotels_form(
    hotel_graph,
    form_data: dict,
    request_id: Optional[str] = None,
) -> HotelSearchResponse:
    """
    Handle a structured form hotel search request.
    
    This is faster than NLP because the form already gives us structured data —
    no AI call needed for parsing. The LangGraph will skip the LLM in Node 1.
    
    form_data example:
        {"city": "Goa", "city_iata": "GOI", "check_in_date": "2025-06-14", ...}
    """
    try:
        logger.info(
            "Hotel form search: %s (%s → %s)",
            form_data.get("city"),
            form_data.get("check_in_date"),
            form_data.get("check_out_date"),
        )

        # Build initial state and run the graph
        initial_state = _build_initial_state(form_data)
        final_state   = hotel_graph.invoke(initial_state)

        return _build_response(final_state, request_id=request_id)

    except Exception as exc:
        logger.exception("Hotel form search failed: %s", exc)
        return HotelSearchResponse(
            status="error",
            message=f"Hotel search failed: {str(exc)}",
            request_id=request_id,
            error_detail=str(exc),
            hotel_count=0,
        )