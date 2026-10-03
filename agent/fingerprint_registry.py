"""
agent/fingerprint_registry.py
================================

The rug-pull defense — see week-6-notes.md, section 5's "Rug Pull
(Silent Redefinition)" attack class: a tool's description/schema
changes after it has already been approved, and most MCP clients never
re-prompt the user when that happens.

This module fixes that gap explicitly: every tool discovered from an
MCP server is fingerprinted (a hash of its name + description + input
schema) and compared against a stored, previously-approved fingerprint.
A tool whose fingerprint doesn't match its approved one is EXCLUDED
from the agent's available toolset until a human explicitly
re-approves it — see agent/mcp_client.py, which calls this registry
right after raw MCP discovery and BEFORE any tool is wrapped for
LangChain or bound to a model.

Operates on raw MCP protocol data (mcp.types.Tool: `.name`,
`.description`, `.inputSchema`) rather than on LangChain-wrapped tool
objects, deliberately — checking at the protocol boundary, before
trusting a schema enough to even wrap it, is the more defensible place
for a security check to live (see this module's use in mcp_client.py).
"""

import hashlib
import json
from dataclasses import dataclass


@dataclass
class FingerprintCheckResult:
    """
    The outcome of checking one discovered tool against the registry.

    Attributes:
        tool_name: Name of the tool checked.
        fingerprint: The fingerprint computed from its CURRENT schema.
        approved: True if this fingerprint matches a previously
            approved one.
        is_new: True if this tool had no prior approved fingerprint at all.
        is_changed: True if this tool WAS previously approved under a
            DIFFERENT fingerprint — the actual rug-pull signal.
    """

    tool_name: str
    fingerprint: str
    approved: bool
    is_new: bool
    is_changed: bool


def compute_fingerprint(name: str, description: str, input_schema: dict) -> str:
    """
    Compute a stable fingerprint for a tool's identity: its name,
    description, and parameter schema.

    Args:
        name: Tool name.
        description: Tool description (this is exactly the text a
            tool-poisoning attack would try to manipulate — see
            week-6-notes.md section 5).
        input_schema: The tool's JSON schema for its parameters.

    Returns:
        A hex-encoded SHA-256 hash. Using `sort_keys=True` in the JSON
        serialization ensures the hash is stable regardless of key
        ordering in the schema dict, so two semantically-identical
        schemas never produce different fingerprints due to ordering alone.
    """
    payload = json.dumps(
        {"name": name, "description": description, "input_schema": input_schema}, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ToolFingerprintRegistry:
    """
    Stores approved tool fingerprints and checks newly-discovered tools
    against them.

    Kept as a simple in-memory dict here (constructor accepts an
    initial mapping so tests and callers can seed/inspect it directly)
    — a production deployment would back this with a persistent store
    (a file, a database row per tool) so approvals survive a client
    restart; see README.md for that extension point.
    """

    def __init__(self, approved_fingerprints: dict[str, str] | None = None) -> None:
        """
        Args:
            approved_fingerprints: Optional initial mapping of
                tool_name -> approved fingerprint hash.
        """
        self._approved: dict[str, str] = dict(approved_fingerprints or {})

    def check(self, name: str, description: str, input_schema: dict) -> FingerprintCheckResult:
        """
        Check a discovered tool's current schema against the registry.

        Args:
            name: Tool name as discovered from the MCP server.
            description: Tool description as discovered.
            input_schema: Tool parameter schema as discovered.

        Returns:
            A FingerprintCheckResult. Does NOT mutate the registry —
            see approve() for explicitly recording a fingerprint as
            approved. This separation means "checking" and "approving"
            are two distinct, auditable actions rather than one
            implicit side effect.
        """
        fingerprint = compute_fingerprint(name, description, input_schema)
        previously_approved = self._approved.get(name)

        is_new = previously_approved is None
        is_changed = previously_approved is not None and previously_approved != fingerprint
        approved = previously_approved == fingerprint

        return FingerprintCheckResult(
            tool_name=name,
            fingerprint=fingerprint,
            approved=approved,
            is_new=is_new,
            is_changed=is_changed,
        )

    def approve(self, name: str, fingerprint: str) -> None:
        """
        Explicitly record a fingerprint as approved for a tool name —
        the human-in-the-loop action that should follow reviewing a
        NEW or CHANGED tool (see week-6-notes.md section 5's mitigation:
        "show the full tool schema at approval time, and re-prompt on
        ANY description change").
        """
        self._approved[name] = fingerprint

    def approved_fingerprints(self) -> dict[str, str]:
        """Return a copy of the current approved-fingerprint mapping (for persistence/inspection)."""
        return dict(self._approved)
