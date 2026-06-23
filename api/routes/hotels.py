import logging
from fastapi import APIRouter, Request, HTTPException, Depends

from models.api_models import (
    HotelNLPSearchRequest,
    HotelFormSearchRequest,
    HotelSearchResponse,
)
from services.hotel_service import search_hotels_nlp, search_hotels_form
from api.middleware.rate_limit import check_rate_limit


# Create a logger labeled with this file's name — for clean log messages
logger = logging.getLogger(__name__)


# Every URL in this file will start with /hotels
router = APIRouter(prefix="/hotels")


# ────────────────────────────────────────────────────────────
#  API 1 — Natural Language Hotel Search
#  URL: POST /api/v1/hotels/search/nlp
# ────────────────────────────────────────────────────────────

@router.post(
    "/search/nlp",
    response_model=HotelSearchResponse,
    summary="Search hotels using plain English",
)
async def hotel_nlp_search(
    body: HotelNLPSearchRequest,
    request: Request,
) -> HotelSearchResponse:
    """
    Example request body:
        { "message": "hotels in Goa for 2 nights next Friday under 5000" }
    """

    # Step 1: Block this user if they've made too many requests recently
    check_rate_limit(request)

    # Step 2: Get the unique ID for this request (for tracking/logging)
    request_id = getattr(request.state, "request_id", None)

    # Step 3: Get the pre-built hotel agent (loaded once when server started)
    hotel_graph = request.app.state.hotel_graph

    # Step 4: Run the agent — this is where the actual work happens
    result = await search_hotels_nlp(
        hotel_graph=hotel_graph,
        message=body.message,
        request_id=request_id,
    )

    # Step 5: If something broke internally, tell the frontend clearly
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_detail)

    # Step 6: Send the result back to the frontend
    return result


# ────────────────────────────────────────────────────────────
#  API 2 — Structured Form Hotel Search
#  URL: POST /api/v1/hotels/search/form
# ────────────────────────────────────────────────────────────

@router.post(
    "/search/form",
    response_model=HotelSearchResponse,
    summary="Search hotels using a structured form (city, dates, guests)",
)
async def hotel_form_search(
    body: HotelFormSearchRequest,
    request: Request,
) -> HotelSearchResponse:
    """
    Example request body:
        {
          "city": "Goa",
          "check_in_date": "2025-07-01",
          "check_out_date": "2025-07-03",
          "num_adults": 2
        }
    """

    # Step 1: Block this user if they've made too many requests recently
    check_rate_limit(request)

    # Step 2: Get the unique ID for this request (for tracking/logging)
    request_id = getattr(request.state, "request_id", None)

    # Step 3: Get the pre-built hotel agent
    hotel_graph = request.app.state.hotel_graph

    # Step 4: Run the agent with the form data (no AI parsing needed)
    result = await search_hotels_form(
        hotel_graph=hotel_graph,
        form_data=body.model_dump(),   # convert Pydantic object → plain dict
        request_id=request_id,
    )

    # Step 5: If something broke internally, tell the frontend clearly
    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_detail)

    # Step 6: Send the result back to the frontend
    return result