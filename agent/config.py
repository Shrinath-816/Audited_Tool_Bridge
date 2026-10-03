"""
agent/config.py
=================

Centralized, typed application configuration. See Week 1's config.py
for the full rationale (fail-fast validation, no secrets in source).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Strongly-typed application settings.

    Attributes:
        openrouter_api_key: API key for OpenRouter.
        chat_model: OpenRouter model slug used for the agent's LLM
            calls. Must support tool calling.
        mcp_server_url: URL of the Audited Tool Bridge's MCP server
            (see mcp_server/server.py), running over Streamable HTTP.
        max_iterations: Hard cap on agent loop iterations — see
            agent/safety.py and week-4-notes.md section 4.
        recursion_limit: LangGraph's own graph-level safety valve.
        request_timeout_seconds: Hard timeout for a single LLM call.
    """

    openrouter_api_key: str
    chat_model: str = "anthropic/claude-sonnet-4.5"

    mcp_server_url: str = "http://localhost:8765/mcp"

    max_iterations: int = 8
    recursion_limit: int = 50
    request_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a cached, validated Settings singleton for the process."""
    return Settings()
