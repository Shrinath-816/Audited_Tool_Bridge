"""
test_graph_routing.py
========================

Unit tests for agent/graph.py's route_after_model. Hand-built fake
message objects, no LLM/MCP/graph compilation involved.
"""

from langgraph.graph import END

from agent.graph import route_after_model


class _FakeMessage:
    def __init__(self, tool_calls=None):
        self.tool_calls = tool_calls or []


def test_routes_to_end_when_no_tool_calls() -> None:
    state = {"messages": [_FakeMessage([])], "tool_call_log": []}
    assert route_after_model(state) == END


def test_routes_to_execute_tools_when_tool_calls_present() -> None:
    state = {
        "messages": [_FakeMessage([{"name": "calculate", "args": {"expression": "1+1"}}])],
        "tool_call_log": [],
    }
    assert route_after_model(state) == "execute_tools"


def test_routes_to_force_stop_on_repeated_identical_tool_call() -> None:
    state = {
        "messages": [_FakeMessage([{"name": "get_order_status", "args": {"order_id": "X"}}])],
        "tool_call_log": [
            {"name": "get_order_status", "arguments": {"order_id": "X"}},
            {"name": "get_order_status", "arguments": {"order_id": "X"}},
        ],
    }
    assert route_after_model(state) == "force_stop"
