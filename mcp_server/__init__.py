"""
mcp_server package
====================

The Audited Tool Bridge's MCP server: exposes simulated legacy
enterprise APIs (order lookup, refunds, support tickets, calculation)
as standardized MCP Tools, plus the refund policy as an MCP Resource —
see week-6-notes.md, sections 2-3.

Two security/governance features layered on top of plain tool exposure
(week-6-notes.md, section 5):
- audit_log.py: every tool invocation is logged server-side, independent
  of whatever the calling agent records itself.
- fingerprint_registry.py: the CLIENT side of the bridge uses this
  against tools discovered from this server to detect "rug pull"
  (silent tool redefinition) — see agent/mcp_client.py.
"""
