"""
agent/main.py
===============

FastAPI application entry point for the Audited Tool Bridge's agent
service.

Endpoints:
    POST /chat   - send a message; the agent discovers, fingerprint-
                   checks, curates, and uses tools from the bridge's
                   MCP server to respond
    GET  /health - basic liveness check

Run locally with:
    uvicorn agent.main:app --reload

Requires the MCP server (mcp_server/server.py) to be running first —
see README.md.

Per-request flow (this is the part that differs most from Week 4's
main.py, where tools were static and bound once at startup):
    1. Connect to the MCP server, discover tools, fingerprint-check
       them (agent/mcp_client.py) — flags anything that changed since
       approval (rug-pull defense).
    2. Curate a task-relevant subset of the APPROVED tools for this
       specific message (agent/loadout_selector.py — the context
       engineering "select" lever).
    3. Build and compile a fresh agent graph bound to exactly that
       curated toolset (agent/graph.py), run it, and return the result
       — including which tools (if any) were flagged, so a caller can
       see the rug-pull defense actually working, not just trust that
       it exists.
"""

from fastapi import Depends, FastAPI
from langchain_core.messages import HumanMessage

from agent.config import Settings, get_settings
from agent.fingerprint_registry import ToolFingerprintRegistry
from agent.graph import build_agent_graph
from agent.llm import build_chat_model
from agent.loadout_selector import ToolLoadoutSelector
from agent.mcp_client import connect_bridge
from agent.schemas import ChatRequest, ChatResponse, FlaggedToolSummary, ToolCallSummary

app = FastAPI(
    title="The Audited Tool Bridge",
    description="Week 6 project: legacy APIs exposed as secure, audited MCP tools, safely discovered per request.",
    version="0.1.0",
)

# One fingerprint registry for the process's lifetime — approvals
# persist across requests within one running process (a production
# deployment would back this with durable storage; see
# agent/fingerprint_registry.py's docstring on that extension point).
_registry = ToolFingerprintRegistry()
_loadout_selector = ToolLoadoutSelector()


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic liveness check — does not connect to the MCP server or the LLM provider."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, settings: Settings = Depends(get_settings)) -> ChatResponse:
    """
    Handle one chat request end to end through the audited bridge —
    see module docstring for the full per-request flow.
    """
    llm = build_chat_model(settings)

    async with connect_bridge(settings.mcp_server_url, _registry) as bridge:
        available_names = [tool.name for tool in bridge.approved_tools]
        curated_names = _loadout_selector.select(chat_request.message, available_names)
        curated_tools = [tool for tool in bridge.approved_tools if tool.name in curated_names]

        workflow = build_agent_graph(llm, tools=curated_tools, max_iterations=settings.max_iterations)
        compiled_graph = workflow.compile()

        result = await compiled_graph.ainvoke(
            {
                "messages": [HumanMessage(content=chat_request.message)],
                "iteration_count": 0,
                "tool_call_log": [],
                "stop_reason": "completed",
            },
            config={"recursion_limit": settings.recursion_limit},
        )

        final_message = result["messages"][-1]
        tool_calls = [
            ToolCallSummary(name=record["name"], arguments=record["arguments"])
            for record in result["tool_call_log"]
        ]
        flagged_tools = [
            FlaggedToolSummary(
                tool_name=flag.tool_name,
                reason="changed since approval (possible rug pull)" if flag.is_changed else "not yet approved",
            )
            for flag in bridge.flagged
        ]

        return ChatResponse(
            reply=final_message.content,
            tool_calls=tool_calls,
            flagged_tools=flagged_tools,
            iterations_used=result["iteration_count"],
            stopped_reason=result["stop_reason"],
        )
