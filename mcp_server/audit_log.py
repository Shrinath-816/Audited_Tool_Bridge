"""
mcp_server/audit_log.py
==========================

Server-side audit logging — see week-6-notes.md, section 5's
mitigation table and this project's brief: "heavily audited tools."

Deliberately implemented on the SERVER, not the calling agent: an
audit trail that only the (potentially compromised or buggy) client
maintains is not trustworthy as an audit trail — the server is the
actual execution boundary, so it is the right place to record what
really happened, independent of whatever the agent itself claims to
have done (compare to Week 5's tracing, which is agent-side and
answers a different question: "how did the AGENT reason", not "what
did the SERVER actually execute").
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AuditEntry:
    """
    One recorded tool invocation.

    Attributes:
        tool_name: Name of the tool that was called.
        arguments: Arguments supplied by the caller.
        result: The string result returned (or an error message).
        success: Whether the call completed without raising.
        timestamp: UTC time of the call.
    """

    tool_name: str
    arguments: dict
    result: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditLog:
    """
    Append-only audit log of every tool invocation made through this
    MCP server.

    Kept in memory (for inspection via the `get_audit_log` tool — see
    server.py) AND optionally persisted to a JSON-lines file, so an
    audit trail survives a server restart — a real requirement for
    "heavily audited" tools, not just a nice-to-have.
    """

    def __init__(self, persist_path: str | None = None) -> None:
        """
        Args:
            persist_path: Optional file path to append each entry to as
                a JSON line. If None, entries are kept in memory only
                (fine for local development/tests).
        """
        self._entries: list[AuditEntry] = []
        self._persist_path = Path(persist_path) if persist_path else None

    def record(self, tool_name: str, arguments: dict, result: str, success: bool) -> AuditEntry:
        """
        Record one tool invocation.

        Args:
            tool_name: Name of the tool invoked.
            arguments: Arguments the caller supplied.
            result: The result returned to the caller.
            success: Whether execution succeeded.

        Returns:
            The AuditEntry that was recorded.
        """
        entry = AuditEntry(tool_name=tool_name, arguments=arguments, result=result, success=success)
        self._entries.append(entry)

        if self._persist_path is not None:
            with self._persist_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def recent(self, limit: int = 20) -> list[AuditEntry]:
        """Return the most recent `limit` entries, newest last."""
        return self._entries[-limit:]

    def all_entries(self) -> list[AuditEntry]:
        """Return every recorded entry, oldest first."""
        return list(self._entries)
