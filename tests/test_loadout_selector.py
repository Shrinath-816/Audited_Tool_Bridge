"""
test_loadout_selector.py
===========================

Unit tests for ToolLoadoutSelector — the context engineering "select"
lever. Pure logic, no network.
"""

from agent.loadout_selector import ToolLoadoutSelector

_ALL_TOOLS = ["get_order_status", "issue_refund", "create_support_ticket", "calculate"]


def test_order_related_message_selects_order_tools_only() -> None:
    selector = ToolLoadoutSelector()

    selected = selector.select("What's the status of my order ORD-1001?", _ALL_TOOLS)

    assert set(selected) == {"get_order_status", "issue_refund"}


def test_support_related_message_selects_ticket_tool_only() -> None:
    selector = ToolLoadoutSelector()

    selected = selector.select("I have a problem and need to escalate this issue.", _ALL_TOOLS)

    assert selected == ["create_support_ticket"]


def test_math_related_message_selects_calculator_only() -> None:
    selector = ToolLoadoutSelector()

    selected = selector.select("Can you calculate the total for me?", _ALL_TOOLS)

    assert selected == ["calculate"]


def test_message_matching_multiple_categories_selects_union() -> None:
    selector = ToolLoadoutSelector()

    selected = selector.select("My order was damaged, please open a support ticket.", _ALL_TOOLS)

    assert set(selected) == {"get_order_status", "issue_refund", "create_support_ticket"}


def test_unmatched_message_falls_back_to_all_available_tools() -> None:
    """See loadout_selector.py's design note: under-selecting is worse than over-selecting."""
    selector = ToolLoadoutSelector()

    selected = selector.select("Hello there, how are you?", _ALL_TOOLS)

    assert set(selected) == set(_ALL_TOOLS)


def test_selection_never_includes_tools_outside_available_list() -> None:
    """If a matched tool isn't actually available (e.g. excluded by fingerprint check), it must not appear."""
    selector = ToolLoadoutSelector()
    limited_available = ["get_order_status"]  # issue_refund NOT available this time

    selected = selector.select("I need a refund for my order.", limited_available)

    assert selected == ["get_order_status"]
    assert "issue_refund" not in selected
