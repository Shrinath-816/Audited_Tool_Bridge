"""
test_backend.py
==================

Unit tests for mcp_server/backend.py's simulated legacy system logic —
independent of MCP/FastMCP entirely, since this file has no MCP
concerns in it by design (see its module docstring).
"""

from mcp_server import backend


def test_calculate_basic_arithmetic() -> None:
    assert backend.calculate("12 * (3 + 4)") == "84"


def test_calculate_rejects_unsupported_syntax() -> None:
    result = backend.calculate("__import__('os').system('echo hi')")
    assert "Could not evaluate" in result


def test_get_order_status_known_order() -> None:
    result = backend.get_order_status("ORD-1001")
    assert "delivered" in result and "89.99" in result


def test_get_order_status_unknown_order() -> None:
    assert "No order found" in backend.get_order_status("ORD-9999")


def test_issue_refund_then_reject_second_attempt() -> None:
    first = backend.issue_refund("ORD-1002", "damaged")
    assert "Refund" in first

    second = backend.issue_refund("ORD-1002", "again")
    assert "already been refunded" in second


def test_create_support_ticket_ids_are_unique() -> None:
    t1 = backend.create_support_ticket("Issue A")
    t2 = backend.create_support_ticket("Issue B")
    assert t1 != t2
