from pydantic import BaseModel, Field   # BaseModel = a class that validates data automatically
from typing import Optional             # Optional means the field can be empty (None)

class HotelIntent(BaseModel):
    """
    After the user types something like:
    "Find me a luxury hotel in Goa for 2 nights next Friday under 5000"
    
    The AI will fill in this form with:
        city = "Goa"
        check_in_date = "2025-06-14"
        check_out_date = "2025-06-16"
        budget_per_night_inr = 5000
        hotel_type = "luxury"
    """
    city: Optional[str] = Field(None, description="City name where the user wants to find a hotel, e.g. 'Goa', 'Mumbai'")
    city_iata: Optional[str] = Field(None , description="IATA code for the city, e.g. 'GOI' for Goa, 'BOM' for Mumbai")
    check_in_date: Optional[str] = Field(None, description="Check-in date in YYYY-MM-DD format, e.g. '2025-06-14'")
    check_out_date: Optional[str] = Field(None, description="Check-out date in YYYY-MM-DD format, e.g. '2025-06-16'")
    num_adults: int = Field(1, description="Number of adults staying, default is 1")
    num_children: int = Field(0, description="Number of children staying, default is 0")
    num_rooms: int = Field(1, description="Number of rooms needed, default is 1")
    budget_per_night_inr: Optional[int] = Field(None, description="Maximum price per night in Indian Rupees, e.g. 3000")
    hotel_type: Optional[str] = Field(None, description="Type of hotel the user wants, e.g. 'luxury', 'budget', 'resort', 'hostel'")
    amenities: Optional[str] = Field(None, description="Extra features the user wants, e.g. 'pool, gym, wifi'")
    trip_type: Optional[str] = Field(None, description="Purpose of the trip, e.g. 'honeymoon', 'family', 'business'")
    special_requests: Optional[str] = Field(None, description="Any other special requests the user mentioned")

    
    # These 3 flags tell us if the user clearly mentioned each thing
    # True = user clearly said it | False = we are guessing
    is_city_clear: bool = Field(False)
    is_dates_clear: bool = Field(False)
    is_budget_clear: bool = Field(False)