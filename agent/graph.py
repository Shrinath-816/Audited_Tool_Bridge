"""
agent/graph.py
================

The bridge agent's LangGraph loop — see week-4-notes.md, section 10,
for the full StateGraph/node/edge/cycle rationale. Structurally
identical to Week 4's Persistent Operator (call_model <-> execute_tools
cycle, same safety valves) with ONE key difference: `execute_tools`
invokes real MCP tools (via `tool.ainvoke(args)`) discovered and
fingerprint-checked by agent/mcp_client.py, instead of calling local
Python functions directly — this is what "the same agent loop, now
backed by a standardized, audited tool bridge" means concretely.
"""

import logging

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from agent.safety import has_exceeded_max_iterations, is_repeated_tool_call
from agent.state import AgentState

logger = logging.getLogger(__name__)


def route_after_model(state: AgentState) -> str:
    """
    Conditional edge — module-level and dependency-free so it's
    directly unit-testable (see tests/test_graph_routing.py), following
    the exact same pattern as Week 4's route_after_model.
    """
    last_message = state["messages"][-1]

    if not getattr(last_message, "tool_calls", None):
        return END
    if is_repeated_tool_call(state["tool_call_log"]):
        return "force_stop"
    return "execute_tools"


def build_agent_graph(llm, tools: list[BaseTool], max_iterations: int) -> StateGraph:
    """
    Construct the (uncompiled) agent StateGraph.

    Args:
        llm: A chat model — tool binding happens here, INSIDE this
            function (`llm.bind_tools(tools)`), rather than being
            pre-bound by the caller — see main.py, which passes the
            per-request curated tool subset from
            agent/loadout_selector.py, so a fresh bound model (and
            therefore a fresh graph) is built for every request. This
            mirrors Week 5's eval_runner.py building a fresh graph per
            golden example, for the same underlying reason: the
            configuration genuinely varies per invocation.
        tools: The curated, fingerprint-approved MCP tools for this
            request (see agent/mcp_client.py, agent/loadout_selector.py).
        max_iterations: Hard cap on loop iterations — see agent/safety.py.

    Returns:
        An uncompiled StateGraph — caller must .compile() it.
    """
    bound_llm = llm.bind_tools(tools)
    tools_by_name = {tool.name: tool for tool in tools}

    async def call_model(state: AgentState) -> dict:
        """Invoke the LLM, enforcing the max_iterations safety valve first."""
        next_iteration = state["iteration_count"] + 1

        if has_exceeded_max_iterations(state["iteration_count"], max_iterations=max_iterations):
            logger.warning("Agent loop hit max_iterations=%s; force-stopping.", max_iterations)
            forced_message = AIMessage(
                content=(
                    "I wasn't able to fully complete this within my allotted number of steps. "
                    "Here's what I found so far — let me know if you'd like me to continue."
                )
            )
            return {
                "messages": [forced_message],
                "iteration_count": next_iteration,
                "stop_reason": "max_iterations",
            }

        response = await bound_llm.ainvoke(state["messages"])
        return {"messages": [response], "iteration_count": next_iteration}

    async def execute_tools(state: AgentState) -> dict:
        """
        Execute every tool call requested in the model's last message
        by invoking the corresponding REAL MCP tool (via
        `tool.ainvoke(args)`) — the tool objects here were discovered,
        fingerprint-checked, and curated before this graph was even
        built (see build_agent_graph's docstring).
        """
        last_message = state["messages"][-1]
        tool_messages = []
        new_tool_call_records = []

        for call in last_message.tool_calls:
            name, args, call_id = call["name"], call["args"], call["id"]
            new_tool_call_records.append({"name": name, "arguments": args})

            try:
                if name in tools_by_name:
                    result = await tools_by_name[name].ainvoke(args)
                else:
                    # Should not normally happen (the model can only
                    # request tools it was bound with), but handled
                    # explicitly rather than assumed impossible — see
                    # week-4-notes.md section 2's "never silently
                    # swallow tool errors" guidance.
                    result = f"Error: unknown or unavailable tool '{name}'."
            except Exception as exc:
                result = f"Error executing tool '{name}': {exc}"

            tool_messages.append(ToolMessage(content=str(result), tool_call_id=call_id))

        return {"messages": tool_messages, "tool_call_log": new_tool_call_records}

    def force_stop(state: AgentState) -> dict:
        """Reached when the repeated-identical-tool-call safety valve fires."""
        logger.warning("Repeated identical tool call detected; force-stopping.")
        message = AIMessage(
            content=(
                "I seem to be repeating the same action without making progress, so I've "
                "stopped here rather than continue. Could you clarify what you'd like me to do?"
            )
        )
        return {"messages": [message], "stop_reason": "repeated_tool_call"}

    workflow = StateGraph(AgentState)
    workflow.add_node("call_model", call_model)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("force_stop", force_stop)

    workflow.add_edge(START, "call_model")
    workflow.add_conditional_edges("call_model", route_after_model, ["execute_tools", "force_stop", END])
    # THE CYCLE — see week-4-notes.md section 10.
    workflow.add_edge("execute_tools", "call_model")
    workflow.add_edge("force_stop", END)

    return workflow
