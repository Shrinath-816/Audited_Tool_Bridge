"""
agent/state.py
================

LangGraph state schema for the bridge's agent loop — see
week-4-notes.md, section 5, for the full reducer-based state design
rationale. Simpler than Week 4/5's Persistent Operator on purpose:
this project's focus is the MCP tool bridge itself (discovery,
fingerprinting, auditing, curated loadouts), not a full customer-memory
system — see README.md's "Known limitations" for that explicit scope note.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ToolCallRecord(TypedDict):
    """One recorded tool call — used by the repeated-call safety valve and the final API response trace."""

    name: str
    arguments: dict


class AgentState(TypedDict):
    """
    State carried through one agent loop execution.

    Attributes:
        messages: Conversation history — see add_messages reducer notes
            in week-4-notes.md section 5.
        iteration_count: How many times call_model has run this execution.
        tool_call_log: Every tool call made so far, in order — used by
            the repeated-call safety valve (agent/safety.py) and
            surfaced in the API response for traceability.
        stop_reason: Set when a safety valve fires ("max_iterations" /
            "repeated_tool_call"); "completed" otherwise.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    iteration_count: Annotated[int, lambda _old, new: new]
    tool_call_log: Annotated[list[ToolCallRecord], operator.add]
    stop_reason: Annotated[str, lambda _old, new: new]
