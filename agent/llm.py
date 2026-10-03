"""
agent/llm.py
=============

Constructs the LangChain chat model used by the agent.

Uses `langchain-openrouter`'s ChatOpenRouter rather than
ChatOpenAI+base_url override — see week-4-notes.md's llm.py for the
full rationale (LangChain's own docs recommend provider-specific
packages over the base_url-override pattern for non-OpenAI providers).

Unlike Week 4's llm.py, tools are NOT bound here — this project's
tool set is dynamic per request (discovered from MCP, fingerprint-
checked, then curated by the loadout selector — see mcp_client.py and
loadout_selector.py), so binding happens per-request in main.py, not
once at model-construction time.
"""

from langchain_openrouter import ChatOpenRouter

from agent.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenRouter:
    """
    Construct the (tool-unbound) chat model for the agent.

    Args:
        settings: Application settings.

    Returns:
        A ChatOpenRouter instance. Call `.bind_tools(tools)` on the
        result once the per-request curated tool list is known.
    """
    return ChatOpenRouter(
        model=settings.chat_model,
        api_key=settings.openrouter_api_key,
        timeout=settings.request_timeout_seconds,
        temperature=0,
    )
