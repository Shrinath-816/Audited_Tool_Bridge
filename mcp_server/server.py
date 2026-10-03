"""
mcp_server/server.py
=======================

The Audited Tool Bridge's MCP server — see week-6-notes.md, section 3.

Exposes mcp_server/backend.py's simulated legacy functions as MCP
Tools, the refund policy as an MCP Resource, and a
`get_audit_log` tool for inspecting what's been executed — turning
"standardized" (any MCP client can use these) into "standardized AND
audited" (every use is recorded server-side, independent of the
calling agent — see audit_log.py's module docstring).

Run with:
    python -m mcp_server.server

Runs over Streamable HTTP (see week-6-notes.md section 2 on why this
is the current transport for remote/shared servers, as opposed to
stdio for same-machine-only integrations) so it can be shared by
multiple agents/clients, not just one local process.
"""

from mcp.server.fastmcp import FastMCP

from mcp_server import backend
from mcp_server.audit_log import AuditLog

mcp = FastMCP("Legacy Order Management Bridge")

# One AuditLog instance for the server process's lifetime — every tool
# call below records into it before returning. Persisted to a JSON
# lines file so the audit trail survives a restart (see AuditLog's
# persist_path parameter).
_audit_log = AuditLog(persist_path="audit_log.jsonl")


def _run_audited(tool_name: str, arguments: dict, func, *args) -> str:
    """
    Shared execution wrapper: run a backend function, record the
    outcome to the audit log (success or failure), and return the
    result — used by every tool below so audit logging can never be
    accidentally skipped by a tool implementation forgetting to call it.
    """
    try:
        result = func(*args)
        _audit_log.record(tool_name=tool_name, arguments=arguments, result=result, success=True)
        return result
    except Exception as exc:
        error_message = f"Error executing '{tool_name}': {exc}"
        _audit_log.record(tool_name=tool_name, arguments=arguments, result=error_message, success=False)
        return error_message


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Look up the current status, total, and refund state of a customer order by its ID."""
    return _run_audited("get_order_status", {"order_id": order_id}, backend.get_order_status, order_id)


@mcp.tool()
def issue_refund(order_id: str, reason: str) -> str:
    """
    Issue a refund for a customer's order. This is a REAL ACTION with a
    side effect — only call this after confirming the order via
    get_order_status, and only when the user has clearly requested a refund.
    """
    return _run_audited(
        "issue_refund", {"order_id": order_id, "reason": reason}, backend.issue_refund, order_id, reason
    )


@mcp.tool()
def create_support_ticket(summary: str, priority: str = "normal") -> str:
    """Create a support ticket for an issue that needs human follow-up. priority: 'low', 'normal', or 'high'."""
    return _run_audited(
        "create_support_ticket",
        {"summary": summary, "priority": priority},
        backend.create_support_ticket,
        summary,
        priority,
    )


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a basic arithmetic expression (numbers, +, -, *, /, parentheses only)."""
    return _run_audited("calculate", {"expression": expression}, backend.calculate, expression)


@mcp.tool()
def get_audit_log(limit: int = 20) -> str:
    """
    Return the most recent audit log entries for this server, as a
    human-readable summary. Exposed as a tool mainly for demo/inspection
    purposes — see README.md's note on scoping this down (e.g. behind a
    separate, privileged MCP server) in a real deployment rather than
    exposing it alongside general-purpose tools.
    """
    entries = _audit_log.recent(limit=limit)
    if not entries:
        return "No tool calls have been recorded yet."
    lines = [
        f"[{e.timestamp}] {e.tool_name}({e.arguments}) -> "
        f"{'OK' if e.success else 'ERROR'}: {e.result}"
        for e in entries
    ]
    return "\n".join(lines)


@mcp.resource("policy://refund")
def refund_policy() -> str:
    """The company's current refund policy — an MCP Resource, not a Tool, since it's read-only reference content."""
    return backend.REFUND_POLICY_TEXT


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
