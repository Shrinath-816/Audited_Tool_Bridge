"""
agent package
==============

The Audited Tool Bridge's agent side: connects to mcp_server via
MCP (agent/mcp_client.py), defends against rug pulls
(agent/fingerprint_registry.py), curates a per-request tool loadout
(agent/loadout_selector.py — context engineering's "select" lever,
week-6-notes.md section 6), and runs a Week-4-style LangGraph agent
loop (agent/graph.py) over the resulting tools.
"""
