from agent.state import TravelAgentState


def should_search_or_abort(state: TravelAgentState) -> str:
    missing = state.get("missing_fields", [])
    return "abort" if missing else "search"
