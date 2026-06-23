from agent.hotel_state import HotelAgentState


def hotel_should_search_or_abort(state: HotelAgentState) -> str:
    """
    Called automatically by LangGraph after hotel_validate_intent_node.
    
    Reads the missing_fields list from state and decides:
        - missing_fields is EMPTY   → return "search"  → go to hotel_search_node
        - missing_fields has items  → return "abort"   → skip search, go to formatter
    
    Example:
        missing_fields = []                    → "search"  (all good, run the search)
        missing_fields = ["check-in date"]     → "abort"   (something missing, don't search)
    """
    missing = state.get("missing_fields", [])

    if missing:
        return "abort"   # something is wrong — skip the API call
    return "search"      # everything looks good — go search