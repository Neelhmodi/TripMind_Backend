from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class HotelResult(TypedDict):
    hotel_name: str
    hotel_id: str
    address: str
    rating: Optional[float]
    reviews_count: Optional[int]
    hotel_class: str
    room_type: Optional[str]
    price_per_night_inr: Optional[int]
    check_in_date: str
    check_out_date: str
    amenities: List[str]
    images: List[str]
    nearby_places: List[str]
    booking_link: str
    booking_links: dict = {}


class HotelAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # Search parameters
    city: Optional[str]
    city_iata: Optional[str]
    check_in_date: Optional[str]
    check_out_date: Optional[str]
    num_adults: int
    num_children: int
    num_rooms: int
    budget_per_night_inr: Optional[int]
    hotel_type: Optional[str]
    amenities: Optional[str]
    trip_type: Optional[str]
    special_requests: Optional[str]
    # Results
    hotels: List[HotelResult]
    # Flow control
    missing_fields: List[str]
    error_message: Optional[str]

    