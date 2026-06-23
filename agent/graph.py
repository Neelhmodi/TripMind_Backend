from langgraph.graph import StateGraph, START, END
from agent.state import TravelAgentState
from agent.nodes import (
    intent_parser_node,
    validate_intent_node,
    flight_search_node,
    response_formatter_node,
)
from agent.edges import should_search_or_abort


def build_travel_graph():
    graph = StateGraph(TravelAgentState)

    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("validate_intent", validate_intent_node)
    graph.add_node("flight_search", flight_search_node)
    graph.add_node("response_formatter", response_formatter_node)

    graph.add_edge(START, "intent_parser")
    graph.add_edge("intent_parser", "validate_intent")
    graph.add_conditional_edges(
        "validate_intent",
        should_search_or_abort,
        {"search": "flight_search", "abort": "response_formatter"},
    )
    graph.add_edge("flight_search", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()


travel_graph = build_travel_graph()
