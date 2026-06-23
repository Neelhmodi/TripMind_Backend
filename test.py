import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from agent.hotel_graph import hotel_graph
from tools.hotel_booking import build_booking_com_url


# ── Terminal color helpers ────────────────────────────────────────────────────
# These make the terminal output easier to read

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def question(text):
    print(f"\n{YELLOW}{BOLD}  ❓ {text}{RESET}")

def info(label, value):
    print(f"  {DIM}{label:<22}{RESET} {BOLD}{value}{RESET}")

def success(text):
    print(f"\n{GREEN}{BOLD}  ✅ {text}{RESET}")

def error(text):
    print(f"\n{RED}{BOLD}  ❌ {text}{RESET}")

def divider():
    print(f"  {DIM}{'─'*56}{RESET}")


# ── Option selector helper ────────────────────────────────────────────────────

def choose(prompt_text, options: list, allow_skip=False) -> str:
    """
    Show a numbered list of options and ask the user to pick one.
    Returns the selected option string.
    If allow_skip=True, user can press Enter to skip.
    """
    question(prompt_text)
    for i, option in enumerate(options, start=1):
        print(f"    {CYAN}{i}{RESET}. {option}")

    if allow_skip:
        print(f"    {DIM}(press Enter to skip){RESET}")

    while True:
        raw = input(f"\n  {BOLD}Your choice: {RESET}").strip()

        if allow_skip and raw == "":
            return None

        if raw.isdigit() and 1 <= int(raw) <= len(options):
            selected = options[int(raw) - 1]
            print(f"  {GREEN}Selected → {selected}{RESET}")
            return selected

        print(f"  {RED}Please enter a number between 1 and {len(options)}{RESET}")


def ask(prompt_text, allow_skip=False) -> str:
    """
    Ask a free-text question.
    If allow_skip=True, user can press Enter to skip.
    """
    question(prompt_text)
    if allow_skip:
        print(f"  {DIM}(press Enter to skip){RESET}")
    raw = input(f"  {BOLD}Your answer: {RESET}").strip()
    if not raw:
        return None
    return raw


# ── Date builder helpers ──────────────────────────────────────────────────────

def get_upcoming_dates() -> dict:
    """Returns next 14 days as {label: YYYY-MM-DD} for the date picker."""
    today = date.today()
    dates = {}
    for i in range(1, 15):
        d = today + timedelta(days=i)
        label = d.strftime("%A, %d %B %Y")   # e.g. "Friday, 20 June 2025"
        dates[label] = d.isoformat()
    return dates


def pick_date(prompt_text) -> str:
    """Show next 14 days and let user pick one."""
    upcoming = get_upcoming_dates()
    labels = list(upcoming.keys())
    selected_label = choose(prompt_text, labels)
    return upcoming[selected_label]


# ── Main interactive flow ─────────────────────────────────────────────────────

def run_interactive_hotel_search():

    header("🏨  TripMind Hotel Search")
    print(f"\n  {DIM}Answer the questions below to search for hotels.{RESET}")
    print(f"  {DIM}Where options are shown, type the number and press Enter.{RESET}")

    # ── 1. City ───────────────────────────────────────────────────────────────
    city_options = [
        "Mumbai", "Delhi", "Bengaluru", "Goa",
        "Jaipur", "Ahmedabad", "Hyderabad", "Chennai",
        "Kolkata", "Pune", "Kochi", "Other (type manually)",
    ]
    city = choose("Which city do you want a hotel in?", city_options)

    if city == "Other (type manually)":
        city = ask("Type the city name")

    # ── 2. Check-in date ─────────────────────────────────────────────────────
    check_in = pick_date("Select check-in date")

    # ── 3. Check-out date ────────────────────────────────────────────────────
    # Build checkout options starting from day after check-in
    checkin_obj = date.fromisoformat(check_in)
    checkout_labels = {}
    for i in range(1, 15):
        d = checkin_obj + timedelta(days=i)
        nights = "night" if i == 1 else "nights"
        label = f"{d.strftime('%A, %d %B %Y')}  ({i} {nights})"
        checkout_labels[label] = d.isoformat()

    question("Select check-out date")
    checkout_list = list(checkout_labels.keys())
    for i, label in enumerate(checkout_list, start=1):
        print(f"    {CYAN}{i}{RESET}. {label}")

    while True:
        raw = input(f"\n  {BOLD}Your choice: {RESET}").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(checkout_list):
            check_out = checkout_labels[checkout_list[int(raw) - 1]]
            print(f"  {GREEN}Selected → {checkout_list[int(raw)-1]}{RESET}")
            break
        print(f"  {RED}Please enter a number between 1 and {len(checkout_list)}{RESET}")

    # ── 4. Number of adults ───────────────────────────────────────────────────
    adult_choice = choose(
        "How many adults?",
        ["1 adult", "2 adults", "3 adults", "4 adults", "5 adults"],
    )
    num_adults = int(adult_choice.split()[0])

    # ── 5. Number of rooms ────────────────────────────────────────────────────
    room_choice = choose(
        "How many rooms?",
        ["1 room", "2 rooms", "3 rooms", "4 rooms"],
    )
    num_rooms = int(room_choice.split()[0])

    # ── 6. Budget (optional) ─────────────────────────────────────────────────
    budget_choice = choose(
        "What is your budget per night? (INR)",
        [
            "Under ₹1,500",
            "Under ₹3,000",
            "Under ₹5,000",
            "Under ₹8,000",
            "Under ₹15,000",
            "No budget limit",
        ],
    )
    budget_map = {
        "Under ₹1,500":    1500,
        "Under ₹3,000":    3000,
        "Under ₹5,000":    5000,
        "Under ₹8,000":    8000,
        "Under ₹15,000":   15000,
        "No budget limit": None,
    }
    budget = budget_map[budget_choice]

    # ── 7. Hotel type (optional) ──────────────────────────────────────────────
    hotel_type_choice = choose(
        "What type of hotel?",
        ["Any", "Luxury / 5-star", "Resort", "Budget / Economy", "Business hotel", "Hostel"],
    )
    hotel_type = None if hotel_type_choice == "Any" else hotel_type_choice

    # ── 8. Trip type (optional) ───────────────────────────────────────────────
    trip_type_choice = choose(
        "What is the purpose of your trip?",
        ["Any", "Leisure", "Honeymoon / Romantic", "Family with kids", "Business"],
    )
    trip_type = None if trip_type_choice == "Any" else trip_type_choice

    # ── Summary before search ─────────────────────────────────────────────────
    header("🔍  Searching with these details")
    info("City",          city)
    info("Check-in",      check_in)
    info("Check-out",     check_out)
    info("Adults",        num_adults)
    info("Rooms",         num_rooms)
    info("Budget/night",  f"₹{budget}" if budget else "No limit")
    info("Hotel type",    hotel_type or "Any")
    info("Trip type",     trip_type  or "Any")

    # ── Build initial state and run agent ─────────────────────────────────────
    print(f"\n  {DIM}Contacting hotel search... please wait...{RESET}\n")

    initial_state = {
        "messages":             [HumanMessage(content=f"Hotels in {city}")],
        "city":                 city,
        "city_iata":            None,
        "check_in_date":        check_in,
        "check_out_date":       check_out,
        "num_adults":           num_adults,
        "num_children":         0,
        "num_rooms":            num_rooms,
        "budget_per_night_inr": budget,
        "hotel_type":           hotel_type,
        "amenities":            None,
        "trip_type":            trip_type,
        "special_requests":     None,
        "hotels":               [],
        "missing_fields":       [],
        "error_message":        None,
    }

    final_state = hotel_graph.invoke(initial_state)

    # ── Handle errors ─────────────────────────────────────────────────────────
    err = final_state.get("error_message")
    if err:
        error(f"Search failed: {err}")
        return

    missing = final_state.get("missing_fields", [])
    if missing:
        error("Search could not complete. Missing:")
        for m in missing:
            print(f"    - {m}")
        return

    # ── Print results ─────────────────────────────────────────────────────────
    hotels = final_state.get("hotels", [])

    if not hotels:
        error("No hotels found for this search. Try different dates or city.")
        return

    header(f"🏨  Found {len(hotels)} Hotels in {city}")

    for i, hotel in enumerate(hotels, start=1):
        divider()
        print(f"\n  {BOLD}{CYAN}[{i}] {hotel.get('hotel_name', 'Unknown Hotel')}{RESET}")

        rating = hotel.get("rating")
        reviews = hotel.get("reviews_count")
        if rating:
            stars = "⭐" * int(rating)
            review_text = f"  ({reviews} reviews)" if reviews else ""
            print(f"      Rating     : {stars} {rating}{review_text}")

        hotel_class = hotel.get("hotel_class")
        if hotel_class:
            print(f"      Class      : {hotel_class}")

        price = hotel.get("price_per_night_inr")
        if price:
            print(f"      Price/night: {GREEN}₹{price:,}{RESET}")
        else:
            print(f"      Price/night: {DIM}Not available{RESET}")

        amenities = hotel.get("amenities", [])
        if amenities:
            print(f"      Amenities  : {', '.join(amenities[:5])}")

        nearby = hotel.get("nearby_places", [])
        if nearby:
            print(f"      Nearby     : {', '.join(nearby[:3])}")

        link = hotel.get("booking_link")
        if link:
            print(f"      Book at    : {CYAN}{link}{RESET}")

    divider()
    success(f"Search complete! {len(hotels)} hotels found in {city}.")

    # ── Ask if user wants to search again ─────────────────────────────────────
    print(f"\n  {YELLOW}Search again? (y/n): {RESET}", end="")
    again = input().strip().lower()
    if again == "y":
        run_interactive_hotel_search()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run_interactive_hotel_search()
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Search cancelled. Goodbye!{RESET}\n")