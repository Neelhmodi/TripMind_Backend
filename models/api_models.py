from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date


# ── REQUEST MODELS ─────────────────────────────────────────────────────────────

class NLPSearchRequest(BaseModel):
    message: str = Field(..., min_length=5, max_length=1000,
        description="Natural language travel request in English, Hindi, or Hinglish.")


class FormSearchRequest(BaseModel):
    origin_city: str = Field(..., description="Departure city name")
    origin_iata: str = Field(..., min_length=2, max_length=3, description="IATA code e.g. AMD")
    destination_city: str = Field(..., description="Arrival city name")
    destination_iata: str = Field(..., min_length=2, max_length=3, description="IATA code e.g. DEL")
    depart_date: str = Field(..., description="Departure date YYYY-MM-DD")
    return_date: Optional[str] = Field(None)
    num_adults: int = Field(1, ge=1, le=9)
    num_children: int = Field(0, ge=0, le=9)
    budget_inr: Optional[int] = Field(None, ge=0)
    preferred_airline: Optional[str] = Field(None)
    trip_type: Optional[str] = Field(None)
    special_requests: Optional[str] = Field(None, max_length=500)

    @field_validator("depart_date", "return_date", mode="after")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            parsed = date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Date '{v}' must be in YYYY-MM-DD format")
        if parsed < date.today():
            raise ValueError(f"Date '{v}' is in the past. Please choose a future date.")
        return v

    @field_validator("origin_iata", "destination_iata", mode="after")
    @classmethod
    def validate_iata_uppercase(cls, v: str) -> str:
        upper = v.strip().upper()
        if not upper.isalpha():
            raise ValueError(f"IATA code '{v}' must contain letters only")
        return upper


# ── RESPONSE MODELS ────────────────────────────────────────────────────────────

class FlightResult(BaseModel):
    flight_number: str
    airline: str
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    flight_status: Optional[str] = None
    departure_iata: Optional[str] = None
    arrival_iata: Optional[str] = None
    flight_date: Optional[str] = None
    duration_minutes: Optional[int] = None
    stops: Optional[int] = None
    price_inr: Optional[int] = None
    layovers: Optional[List[dict]] = None

    google_search_url: Optional[str] = None

    class Config:
        extra = "ignore"


class SearchMetadata(BaseModel):
    origin_city: Optional[str] = None
    origin_iata: Optional[str] = None
    destination_city: Optional[str] = None
    destination_iata: Optional[str] = None
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    num_adults: int = 1
    num_children: int = 0
    budget_inr: Optional[int] = None
    trip_type: Optional[str] = None
    preferred_airline: Optional[str] = None


class FlightSearchResponse(BaseModel):
    status: str
    message: str
    request_id: Optional[str] = None
    metadata: Optional[SearchMetadata] = None
    outbound_flights: List[FlightResult] = []
    return_flights: List[FlightResult] = []
    missing_fields: List[str] = []
    error_detail: Optional[str] = None
    flight_count: int = 0


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    components: dict = {}


class IATALookupResponse(BaseModel):
    city: str
    iata: Optional[str]
    found: bool


class AirlineListResponse(BaseModel):
    airlines: List[str]


# ── REQUEST MODELS FOR HOTEL SEARCH ──────────────────────────────────────────────────────

class HotelNLPSearchRequest(BaseModel):
    message: str = Field(..., min_length=5, max_length=1000,
        description="Natural language hotel search e.g. 'hotels in Goa for 3 nights next Friday'")
    
class HotelFormSearchRequest(BaseModel):
    city: str = Field(..., description="City name e.g. Goa")
    city_iata: Optional[str] = Field(None, description="IATA code e.g. GOI")
    check_in_date: str = Field(..., description="Check-in date YYYY-MM-DD")
    check_out_date: str = Field(..., description="Check-out date YYYY-MM-DD")
    num_adults: int = Field(1, ge=1, le=9)
    num_children: int = Field(0, ge=0, le=9)
    num_rooms: int = Field(1, ge=1, le=9)
    budget_per_night_inr: Optional[int] = Field(None, ge=0)
    hotel_type: Optional[str] = Field(None)
    amenities: Optional[str] = Field(None, max_length=200)
    trip_type: Optional[str] = Field(None)
    special_requests: Optional[str] = Field(None, max_length=500)

    @field_validator("check_in_date", "check_out_date", mode="after")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            parsed = date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Date '{v}' must be in YYYY-MM-DD format")
        if parsed < date.today():
            raise ValueError(f"Date '{v}' is in the past. Please choose a future date.")
        return v



# ── RESPONSE MODELS ──────────────────────────────────────────────────────────── 

class HotelResult(BaseModel):
    hotel_name: str
    hotel_id: str = ""
    address: str = ""
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    hotel_class: str = ""
    price_per_night_inr: Optional[int] = None
    check_in_date: str = ""
    check_out_date: str = ""
    amenities: List[str] = []
    images: List[str] = []
    nearby_places: List[str] = []
    booking_link: str = ""

    booking_links: dict = {}

    google_search_url: Optional[str] = None

    class Config:
        extra = "ignore"

class HotelSearchMetadata(BaseModel):
    city: Optional[str] = None
    city_iata: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    num_adults: int = 1
    num_children: int = 0
    num_rooms: int = 1
    budget_per_night_inr: Optional[int] = None
    hotel_type: Optional[str] = None
    trip_type: Optional[str] = None

class HotelSearchResponse(BaseModel):
    status: str
    message: str
    request_id: Optional[str] = None
    metadata: Optional[HotelSearchMetadata] = None
    hotels: List[HotelResult] = []
    missing_fields: List[str] = []
    error_detail: Optional[str] = None
    hotel_count: int = 0