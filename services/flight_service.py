import logging
from typing import Optional
from langchain_core.messages import HumanMessage

from tools.iata_lookup import city_to_iata
from models.api_models import FlightSearchResponse, FlightResult, SearchMetadata

logger = logging.getLogger(__name__)

try:
    from parsers.intent_parser import IntentParser
    _intent_parser = IntentParser()
except ValueError as exc:
    _intent_parser = None
    logger.warning("IntentParser could not be initialised: %s", exc)


def _build_initial_state(form_data: dict) -> dict:
    return {
        "messages": [HumanMessage(content=(
            f"{form_data.get('origin_city', '?')} to "
            f"{form_data.get('destination_city', '?')} "
            f"on {form_data.get('depart_date', '?')}"
        ))],
        "origin_city": form_data.get("origin_city"),
        "origin_iata": form_data.get("origin_iata"),
        "destination_city": form_data.get("destination_city"),
        "destination_iata": form_data.get("destination_iata"),
        "depart_date": form_data.get("depart_date"),
        "return_date": form_data.get("return_date"),
        "budget_inr": form_data.get("budget_inr"),
        "num_adults": form_data.get("num_adults", 1),
        "num_children": form_data.get("num_children", 0),
        "trip_type": form_data.get("trip_type"),
        "special_requests": form_data.get("special_requests"),
        "preferred_airline": form_data.get("preferred_airline"),
        "outbound_flights": [],
        "return_flights": [],
        "missing_fields": [],
        "error_message": None,
    }


def _build_response(final_state: dict, request_id: Optional[str] = None) -> FlightSearchResponse:
    error_msg = final_state.get("error_message")
    missing = final_state.get("missing_fields", [])
    outbound = final_state.get("outbound_flights", [])
    returning = final_state.get("return_flights", [])

    if error_msg:
        status = "error"
    elif missing:
        status = "missing_fields"
    elif outbound:
        status = "success"
    else:
        status = "no_results"

    outbound_schemas = [FlightResult(**f) for f in outbound if isinstance(f, dict)]
    return_schemas = [FlightResult(**f) for f in returning if isinstance(f, dict)]

    messages = {
        "success": "Flights found successfully.",
        "no_results": "No flights found for this route and date.",
        "missing_fields": "Search could not complete — required fields are missing.",
        "error": "Search failed due to an internal error.",
    }

    return FlightSearchResponse(
        status=status,
        message=messages.get(status, "Unknown status."),
        request_id=request_id,
        metadata=SearchMetadata(
            origin_city=final_state.get("origin_city"),
            origin_iata=final_state.get("origin_iata"),
            destination_city=final_state.get("destination_city"),
            destination_iata=final_state.get("destination_iata"),
            depart_date=final_state.get("depart_date"),
            return_date=final_state.get("return_date"),
            num_adults=final_state.get("num_adults", 1),
            num_children=final_state.get("num_children", 0),
            budget_inr=final_state.get("budget_inr"),
            trip_type=final_state.get("trip_type"),
            preferred_airline=final_state.get("preferred_airline"),
        ),
        outbound_flights=outbound_schemas,
        return_flights=return_schemas,
        missing_fields=missing,
        error_detail=error_msg,
        flight_count=len(outbound_schemas),
    )


async def search_flights_nlp(travel_graph, message: str, request_id: Optional[str] = None) -> FlightSearchResponse:
    if _intent_parser is None:
        return FlightSearchResponse(
            status="error",
            message="NLP search unavailable: GROQ_API_KEY not configured.",
            request_id=request_id,
            error_detail="GROQ_API_KEY missing",
            flight_count=0,
        )
    try:
        logger.info("NLP parsing: %.80s", message)
        intent = _intent_parser.parse(message)
        origin_iata = intent.origin_iata or city_to_iata(intent.origin_city or "")
        destination_iata = intent.destination_iata or city_to_iata(intent.destination_city or "")

        form_data = {
            "origin_city": intent.origin_city,
            "origin_iata": origin_iata,
            "destination_city": intent.destination_city,
            "destination_iata": destination_iata,
            "depart_date": intent.departure_date,
            "return_date": intent.return_date,
            "budget_inr": intent.budget_inr,
            "num_adults": intent.num_adults,
            "num_children": intent.num_children,
            "trip_type": intent.trip_type,
            "special_requests": intent.special_requests,
            "preferred_airline": intent.preferred_airline,
        }
        initial_state = _build_initial_state(form_data)
        initial_state["messages"] = [HumanMessage(content=message)]
        final_state = travel_graph.invoke(initial_state)
        return _build_response(final_state, request_id=request_id)
    except Exception as exc:
        logger.exception("NLP search failed: %s", exc)
        return FlightSearchResponse(
            status="error",
            message=f"Search failed: {str(exc)}",
            request_id=request_id,
            error_detail=str(exc),
            flight_count=0,
        )


async def search_flights_form(travel_graph, form_data: dict, request_id: Optional[str] = None) -> FlightSearchResponse:
    try:
        logger.info("Form search: %s -> %s on %s",
            form_data.get("origin_iata"), form_data.get("destination_iata"), form_data.get("depart_date"))
        initial_state = _build_initial_state(form_data)
        final_state = travel_graph.invoke(initial_state)
        return _build_response(final_state, request_id=request_id)
    except Exception as exc:
        logger.exception("Form search failed: %s", exc)
        return FlightSearchResponse(
            status="error",
            message=f"Search failed: {str(exc)}",
            request_id=request_id,
            error_detail=str(exc),
            flight_count=0,
        )
