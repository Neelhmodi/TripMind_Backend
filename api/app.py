import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.flights import router as flights_router
from api.routes.health  import router as health_router
from api.routes.auth    import router as auth_router
from api.routes.hotels  import router as hotels_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # logger.info("TripMind AI — starting up...")
    try:
        from agent.graph import travel_graph
        app.state.travel_graph = travel_graph
        # logger.info("LangGraph travel_graph loaded ✓")
    except Exception as exc:
        # logger.error(f"Failed to load travel_graph: {exc}")
        raise

    try:
        from agent.hotel_graph import hotel_graph
        app.state.hotel_graph = hotel_graph
        # logger.info("LangGraph hotel_graph loaded ✓")
    except Exception as exc:
        # logger.error(f"Failed to load hotel_graph: {exc}")
        raise
    
    yield
    # logger.info("TripMind AI — shutting down...")

app = FastAPI(
    title="TripMind AI — Flight Search API",
    description="AI-powered flight search. Accepts natural language or structured form data.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    request.state.request_id = request_id
    logger.info(f"[{request_id[:8]}] → {request.method} {request.url.path}")
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    logger.info(f"[{request_id[:8]}] ← {response.status_code}  ({duration_ms:.1f}ms)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "request_id": request_id},
    )


app.include_router(health_router,  prefix="/api/v1", tags=["Health"])
app.include_router(auth_router,    prefix="/api/v1", tags=["Auth"])
app.include_router(flights_router, prefix="/api/v1", tags=["Flights"])
app.include_router(hotels_router,  prefix="/api/v1", tags=["Hotels"])

@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "TripMind AI Flight Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }