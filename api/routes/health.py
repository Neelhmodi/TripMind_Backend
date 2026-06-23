import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from models.api_models import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check(request: Request) -> HealthResponse:
    components = {}
    overall_ok = True

    try:
        graph = request.app.state.travel_graph
        components["travel_graph"] = "ok" if graph is not None else "not_loaded"
        if graph is None:
            overall_ok = False
    except AttributeError:
        components["travel_graph"] = "not_loaded"
        overall_ok = False

    for key in ["SERPAPI_KEY"]:
        if os.environ.get(key):
            components[key] = "present"
        else:
            components[key] = "MISSING"
            overall_ok = False

    for key in ["GROQ_API_KEY"]:
        components[key] = "present" if os.environ.get(key) else "missing (NLP disabled)"

    return HealthResponse(
        status="ok" if overall_ok else "degraded",
        service="TripMind AI Flight Search API",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )
