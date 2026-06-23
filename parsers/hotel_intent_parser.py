import os
from datetime import date, timedelta    # date = today's date, timedelta = adding days
from dotenv import load_dotenv          
from langchain_groq import ChatGroq     
from parsers.hotel_intent_model import HotelIntent  # the form the AI fills in

load_dotenv()  


def _build_hotel_system_prompt() -> str:
    """
    This function creates the instruction message we send to the AI.
    It tells the AI exactly how to understand the user's hotel request.
    
    We also calculate the exact dates for "next Monday", "next Friday" etc.
    so the AI doesn't have to guess.
    """

    # Get today's date and day name e.g. "2025-06-11" and "Wednesday"
    today = date.today()
    weekday = today.strftime("%A")

    # Calculate the exact date for each upcoming weekday
    # e.g. "next Friday" = "2025-06-13"
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_idx = today.weekday()  # Monday=0, Tuesday=1 ... Sunday=6

    next_days = {}
    for i, day_name in enumerate(days_of_week):
        diff = (i - today_idx) % 7   # how many days until that day
        if diff == 0:
            diff = 7                 # if today is that day, go to NEXT week
        next_days[day_name] = (today + timedelta(days=diff)).isoformat()

    # Format as readable text for the AI prompt
    # e.g. "   next Friday = 2025-06-13"
    next_days_str = "\n".join(
        f"   next {day} = {dt}" for day, dt in next_days.items()
    )

    # Return the full instruction string for the AI
    return f"""You are a hotel booking assistant for an Indian travel website.
Read the user's message and extract hotel search details.

Today is: {today.isoformat()} ({weekday})

EXACT DATES FOR UPCOMING DAYS:
{next_days_str}

RULES (follow these strictly):
1.  "next Friday" → use the exact date listed above.
2.  "this weekend" → check_in = next Saturday, check_out = next Sunday.
3.  "for 3 nights" → check_out_date = check_in_date + 3 days.
4.  "with 3 friends" = 4 adults total. "just me" = 1 adult.
5.  Budget: "2k per night" or "Rs 2000" → store as integer 2000.
6.  City codes: Delhi=DEL, Mumbai=BOM, Bengaluru=BLR, Ahmedabad=AMD, Goa=GOI,
    Kolkata=CCU, Chennai=MAA, Hyderabad=HYD, Pune=PNQ, Jaipur=JAI,
    Kochi=COK, Lucknow=LKO, Vadodara=BDQ, Dubai=DXB, Singapore=SIN.
7.  Hotel type: "resort"→ resort | "cheap/budget"→ budget | "5-star"→ luxury | "hostel"→ hostel.
8.  Trip type: "honeymoon"→ romantic | "with kids"→ family | "business"→ business.
9.  Amenities: pick keywords like "pool", "wifi", "gym", "spa", "breakfast".
10. "2 rooms" → num_rooms = 2. Default is 1 room.
11. Set is_*_clear = True ONLY if the user clearly stated it. Do NOT guess.
12. If something is not mentioned, leave it as null. Do NOT fill in guesses.
"""


class HotelIntentParser:
    """
    This class connects to the Groq AI and uses it to read hotel requests.
    
    Usage:
        parser = HotelIntentParser()
        result = parser.parse("I need a hotel in Goa for 2 nights next Friday")
        print(result.city)        # "Goa"
        print(result.check_in_date)  # "2025-06-13"
    """

    def __init__(self):
        # Get the Groq API key from .env file
        groq_api_key = os.environ.get("GROQ_API_KEY")

        # If the key is missing, stop immediately with a clear error message
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in .env file")

        # Connect to the Groq AI model
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,           # 0 = consistent answers, no randomness
            api_key=groq_api_key,
        )

        # Tell the AI to always return a HotelIntent object (structured output)
        # This means we get back a proper Python object, not plain text
        self.structured_llm = llm.with_structured_output(HotelIntent)

    def parse(self, user_message: str) -> HotelIntent:
        """
        Send the user's message to the AI and get back a filled HotelIntent form.
        
        Example:
            Input:  "hotels in Goa under 3000 next weekend"
            Output: HotelIntent(city="Goa", check_in_date="2025-06-14", 
                                budget_per_night_inr=3000, ...)
        """
        messages = [
            ("system", _build_hotel_system_prompt()),  # AI instructions
            ("human", user_message),                   # what the user typed
        ]
        return self.structured_llm.invoke(messages)    # AI fills in the form