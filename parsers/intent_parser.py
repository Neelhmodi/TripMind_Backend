import os
from datetime import date, timedelta
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from parsers.intent_model import TravelIntent

load_dotenv()


def _build_system_prompt() -> str:
    today = date.today()
    weekday = today.strftime("%A")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_idx = today.weekday()
    next_days = {}
    for i, day_name in enumerate(days_of_week):
        diff = (i - today_idx) % 7
        if diff == 0:
            diff = 7
        next_days[day_name] = (today + timedelta(days=diff)).isoformat()

    next_days_str = "\n".join(f"   next {day} = {dt}" for day, dt in next_days.items())

    return f"""You are a travel intent extractor for an Indian travel booking assistant.

Today is: {today.isoformat()} ({weekday})

NEXT WEEKDAY REFERENCE:
{next_days_str}

RULES:
1. For "next <weekday>", use the exact date from above.
2. "this weekend" → use next Saturday's date.
3. "for 3 days" → return_date = departure_date + 3 days.
4. "with 3 friends" = 4 adults. "just me" = 1.
5. Budget: "10k", "10,000", "Rs 10000" → integer 10000.
6. IATA codes: Delhi=DEL, Mumbai=BOM, Bengaluru=BLR, Ahmedabad=AMD, Goa=GOI,
   Kolkata=CCU, Chennai=MAA, Hyderabad=HYD, Pune=PNQ, Jaipur=JAI,
   Kochi=COK, Lucknow=LKO, Vadodara=BDQ, Chandigarh=IXC, Dubai=DXB,
   Singapore=SIN, London=LHR, Bangkok=BKK.
7. Set is_*_clear = True ONLY when explicitly stated.
8. trip_type: "honeymoon"→ romantic, "with kids"→ family, "trek"→ adventure, "meeting"→ business.
9. preferred_airline: "only IndiGo"→ "IndiGo", "air india"→ "Air India".
10. If not mentioned, leave null. Do NOT guess.
"""


import httpx

class IntentParser:
    def __init__(self):
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=groq_api_key,
            http_client=httpx.Client(http2=False),
        )
        self.structured_llm = self.llm.with_structured_output(TravelIntent)

    def parse(self, user_message: str) -> TravelIntent:
        messages = [
            ("system", _build_system_prompt()),
            ("human", user_message),
        ]
        return self.structured_llm.invoke(messages)
