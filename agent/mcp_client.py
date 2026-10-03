"""
agent/mcp_client.py
=====================

Connects to the Audited Tool Bridge's MCP server (mcp_server/server.py)
over Streamable HTTP, and is the ONE place where the rug-pull defense
(agent/fingerprint_registry.py) is enforced — see week-6-notes.md,
section 5: every discovered tool is fingerprint-checked BEFORE it is
ever wrapped as a LangChain tool or handed to a model, so a
poisoned/rug-pulled tool is excluded at the earliest possible point,
not merely flagged after the fact.

Two-step discovery, deliberately in this order:
  1. Raw MCP `session.list_tools()` — gives us exactly `.name`,
     `.description`, `.inputSchema` for fingerprinting, with no
     LangChain-specific wrapping in the way.
  2. `langchain_mcp_adapters.tools.load_mcp_tools(session)` — wraps the
     SAME session's tools as LangChain BaseTool objects, which are
     then filtered down to only the names that passed step 1's check.

Both steps use the SAME underlying ClientSession/connection, since
LangChain-wrapped MCP tools call back into the session when invoked —
the connection must stay open for as long as the tools are usable,
which is why `connect_bridge` is an async context manager rather than
a function that returns a static list.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, NamedTuple

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from agent.fingerprint_registry import FingerprintCheckResult, ToolFingerprintRegistry

logger = logging.getLogger(__name__)


class BridgeConnection(NamedTuple):
    """
    Result of connecting to the bridge and running the fingerprint check.

    Attributes:
        approved_tools: LangChain-wrapped tools whose fingerprint
            matched (or was newly approved — see connect_bridge's
            auto_approve_new parameter) — safe to bind to a model.
        flagged: FingerprintCheckResult entries for tools that were
            EXCLUDED because their fingerprint changed since last
            approval (the actual rug-pull signal) — surfaced so a
            caller can log/alert on this, per week-6-notes.md section
            5's "re-prompt on any description change" mitigation.
    """

    approved_tools: list[BaseTool]
    flagged: list[FingerprintCheckResult]


@asynccontextmanager
async def connect_bridge(
    server_url: str, registry: ToolFingerprintRegistry, auto_approve_new: bool = True
) -> AsyncIterator[BridgeConnection]:
    """
    Connect to the bridge's MCP server and yield its fingerprint-checked tools.

    Args:
        server_url: URL of the MCP server (Streamable HTTP).
        registry: The fingerprint registry to check discovered tools
            against (and, for new tools, to record approvals into —
            see auto_approve_new).
        auto_approve_new: If True (the default, suited to local
            development/this project's scope), a tool seen for the
            FIRST time is automatically approved. A production
            deployment would instead surface brand-new tools for
            explicit human review before approving them — see
            week-6-notes.md section 5's approval-workflow guidance —
            set this False and call `registry.approve(...)` from your
            own review step instead.

    Yields:
        A BridgeConnection with the approved, LangChain-ready tools and
        any flagged (changed-since-approval) tools.
    """
    async with streamablehttp_client(server_url) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()

            raw_tools_response = await session.list_tools()
            approved_names: set[str] = set()
            flagged: list[FingerprintCheckResult] = []

            for raw_tool in raw_tools_response.tools:
                result = registry.check(
                    name=raw_tool.name,
                    description=raw_tool.description or "",
                    input_schema=raw_tool.inputSchema or {},
                )

                if result.approved:
                    approved_names.add(raw_tool.name)
                elif result.is_new and auto_approve_new:
                    registry.approve(raw_tool.name, result.fingerprint)
                    approved_names.add(raw_tool.name)
                    logger.info("Auto-approved new tool '%s'.", raw_tool.name)
                elif result.is_changed:
                    # THE RUG-PULL CASE: exclude this tool entirely
                    # rather than trusting a schema that changed since
                    # it was last approved.
                    logger.warning(
                        "Tool '%s' fingerprint changed since approval — excluding until re-approved.",
                        raw_tool.name,
                    )
                    flagged.append(result)
                else:
                    flagged.append(result)

            all_langchain_tools = await load_mcp_tools(session)
            approved_tools = [tool for tool in all_langchain_tools if tool.name in approved_names]

            yield BridgeConnection(approved_tools=approved_tools, flagged=flagged)
