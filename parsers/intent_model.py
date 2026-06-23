from pydantic import BaseModel, Field
from typing import Optional


class TravelIntent(BaseModel):
    origin_city: Optional[str] = Field(None)
    origin_iata: Optional[str] = Field(None)
    destination_city: Optional[str] = Field(None)
    destination_iata: Optional[str] = Field(None)
    departure_date: Optional[str] = Field(None)
    return_date: Optional[str] = Field(None)
    num_adults: int = Field(1)
    num_children: int = Field(0)
    budget_inr: Optional[int] = Field(None)
    trip_type: Optional[str] = Field(None)
    trip_duration_days: Optional[int] = Field(None)
    special_requests: Optional[str] = Field(None)
    preferred_airline: Optional[str] = Field(None)
    is_origin_clear: bool = Field(False)
    is_destination_clear: bool = Field(False)
    is_dates_clear: bool = Field(False)
    is_budget_clear: bool = Field(False)
