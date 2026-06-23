from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class FlightResult(TypedDict):
    flight_number: str
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    flight_status: str
    departure_iata: str
    arrival_iata: str
    flight_date: str
    duration_minutes: Optional[int]
    stops: Optional[int]
    price_inr: Optional[int]
    layovers: Optional[List[dict]]


class TravelAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    origin_city: Optional[str]
    origin_iata: Optional[str]
    destination_city: Optional[str]
    destination_iata: Optional[str]
    depart_date: Optional[str]
    return_date: Optional[str]
    budget_inr: Optional[int]
    num_adults: int
    num_children: int
    trip_type: Optional[str]
    special_requests: Optional[str]
    preferred_airline: Optional[str]
    outbound_flights: List[FlightResult]
    return_flights: List[FlightResult]
    error_message: Optional[str]
    missing_fields: List[str]
