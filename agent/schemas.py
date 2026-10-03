"""
agent/schemas.py
==================

Pydantic models for the HTTP API's request/response bodies.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str = Field(..., min_length=1)


class ToolCallSummary(BaseModel):
    """One tool call made during this request's agent loop."""

    name: str
    arguments: dict


class FlaggedToolSummary(BaseModel):
    """
    A tool that was EXCLUDED from this request's toolset because its
    fingerprint changed since last approval — the rug-pull signal
    surfaced to the API caller (see agent/fingerprint_registry.py).
    """

    tool_name: str
    reason: str


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    reply: str
    tool_calls: list[ToolCallSummary]
    flagged_tools: list[FlaggedToolSummary]
    iterations_used: int
    stopped_reason: str
