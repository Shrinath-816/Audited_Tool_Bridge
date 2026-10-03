"""
test_audit_log.py
====================

Unit tests for AuditLog. No network — file persistence is exercised
against a temp path via pytest's tmp_path fixture.
"""

import json

from mcp_server.audit_log import AuditLog


def test_record_and_recent_return_recorded_entries() -> None:
    log = AuditLog()

    log.record("get_order_status", {"order_id": "ORD-1001"}, "delivered", success=True)
    log.record("issue_refund", {"order_id": "ORD-1001", "reason": "damaged"}, "refunded", success=True)

    recent = log.recent(limit=10)
    assert len(recent) == 2
    assert recent[0].tool_name == "get_order_status"
    assert recent[1].tool_name == "issue_refund"


def test_recent_respects_limit() -> None:
    log = AuditLog()
    for i in range(5):
        log.record("calculate", {"expression": f"{i}+1"}, str(i + 1), success=True)

    assert len(log.recent(limit=2)) == 2


def test_failed_call_is_recorded_with_success_false() -> None:
    log = AuditLog()

    log.record("issue_refund", {"order_id": "BAD"}, "Error: no order found", success=False)

    entry = log.all_entries()[0]
    assert entry.success is False
    assert "Error" in entry.result


def test_persist_path_writes_json_lines(tmp_path) -> None:
    """When a persist_path is given, every record() call should append one JSON line to it."""
    persist_file = tmp_path / "audit.jsonl"
    log = AuditLog(persist_path=str(persist_file))

    log.record("calculate", {"expression": "2+2"}, "4", success=True)
    log.record("calculate", {"expression": "3+3"}, "6", success=True)

    lines = persist_file.read_text().strip().splitlines()
    assert len(lines) == 2

    first_entry = json.loads(lines[0])
    assert first_entry["tool_name"] == "calculate"
    assert first_entry["result"] == "4"


def test_all_entries_returns_everything_in_order() -> None:
    log = AuditLog()
    log.record("a", {}, "1", True)
    log.record("b", {}, "2", True)
    log.record("c", {}, "3", True)

    names = [e.tool_name for e in log.all_entries()]
    assert names == ["a", "b", "c"]
