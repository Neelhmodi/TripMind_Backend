from langgraph.graph import StateGraph, START, END
from agent.hotel_state import HotelAgentState
from agent.hotel_node import (
    hotel_intent_parser_node,
    hotel_validate_intent_node,
    hotel_search_node,
    hotel_response_formatter_node,
)
from agent.hotel_edges import hotel_should_search_or_abort


def build_hotel_graph():
    graph = StateGraph(HotelAgentState)

    graph.add_node("hotel_intent_parser", hotel_intent_parser_node)
    graph.add_node("hotel_validate_intent", hotel_validate_intent_node)
    graph.add_node("hotel_search", hotel_search_node)
    graph.add_node("hotel_response_formatter", hotel_response_formatter_node)

    graph.add_edge(START, "hotel_intent_parser")
    graph.add_edge("hotel_intent_parser", "hotel_validate_intent")
    graph.add_conditional_edges(
        "hotel_validate_intent",
        hotel_should_search_or_abort,
        {"search": "hotel_search", "abort": "hotel_response_formatter"},
    )
    graph.add_edge("hotel_search", "hotel_response_formatter")
    graph.add_edge("hotel_response_formatter", END)

    return graph.compile()


hotel_graph = build_hotel_graph()