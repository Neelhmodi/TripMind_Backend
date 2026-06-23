import logging
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from models.api_models import (
    NLPSearchRequest,
    FormSearchRequest,
    FlightSearchResponse,
    IATALookupResponse,
    AirlineListResponse,
)
from services.flight_service import search_flights_nlp, search_flights_form
from api.middleware.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flights")

AIRLINES = [
    "IndiGo", "Air India", "Air India Express", "Akasa Air",
    "SpiceJet", "Vistara", "Emirates", "Qatar Airways",
    "Singapore Airlines", "Lufthansa", "British Airways",
]


@router.post("/search/nlp", response_model=FlightSearchResponse, summary="NLP flight search")
async def nlp_search(
    body: NLPSearchRequest,
    request: Request,
) -> FlightSearchResponse:
    """Natural-language flight search using AI parsing."""
    check_rate_limit(request)
    request_id = getattr(request.state, "request_id", None)
    travel_graph = request.app.state.travel_graph

    result = await search_flights_nlp(
        travel_graph=travel_graph,
        message=body.message,
        request_id=request_id,
    )
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_detail)
    return result


@router.post("/search/form", response_model=FlightSearchResponse, summary="Form-based flight search")
async def form_search(
    body: FormSearchRequest,
    request: Request,
) -> FlightSearchResponse:
    """Structured form search — skips LLM, faster and cheaper."""
    check_rate_limit(request)
    request_id = getattr(request.state, "request_id", None)
    travel_graph = request.app.state.travel_graph

    result = await search_flights_form(
        travel_graph=travel_graph,
        form_data=body.model_dump(),
        request_id=request_id,
    )
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_detail)
    return result


@router.get("/iata/{city}", response_model=IATALookupResponse, summary="IATA code lookup")
async def lookup_iata(
    city: str,
) -> IATALookupResponse:
    """Look up IATA airport code for a city name."""
    from tools.iata_lookup import city_to_iata
    iata = city_to_iata(city)
    return IATALookupResponse(city=city, iata=iata if iata else None, found=bool(iata))


@router.get("/airlines", response_model=AirlineListResponse, summary="List airlines")
async def list_airlines() -> AirlineListResponse:
    """Returns available airline filter options."""
    return AirlineListResponse(airlines=AIRLINES)
