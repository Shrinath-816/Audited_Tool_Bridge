"""
agent/loadout_selector.py
============================

The context engineering "select" lever, made concrete — see
week-6-notes.md, section 6: rather than always binding every approved
tool to the model regardless of the task, curate a task-relevant
subset per request. This directly targets the documented "context
confusion" failure mode (the Berkeley Function-Calling Leaderboard
finding cited in the notes: every tested model performs WORSE with
more available tools, independent of context-length limits).

Kept as simple, fast, deterministic keyword heuristics rather than an
LLM call — mirrors Week 3's retrieval-routing guidance: don't spend an
extra model call on a routing decision a cheap heuristic can make
reliably enough, especially for a small, well-understood tool catalog
like this one. A larger or more ambiguous catalog would be a
reasonable place to graduate to an LLM-based or embedding-based
router instead (see week-3-notes.md's routing approaches).
"""

import re

# Keyword categories mapped to the tool(s) relevant to that category.
# Deliberately data, not a chain of if/elif, so adding a new category
# is a one-line change here rather than new branching logic.
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "order": ["order", "refund", "delivery", "shipment", "package"],
    "support": ["ticket", "issue", "complaint", "problem", "escalate"],
    "math": ["calculate", "total", "sum", "how much", "cost of"],
}

_CATEGORY_TOOLS: dict[str, list[str]] = {
    "order": ["get_order_status", "issue_refund"],
    "support": ["create_support_ticket"],
    "math": ["calculate"],
}


class ToolLoadoutSelector:
    """
    Selects a curated subset of tool NAMES relevant to a given user
    message, from the full set of currently-approved tool names.
    """

    def select(self, message: str, available_tool_names: list[str]) -> list[str]:
        """
        Args:
            message: The user's message driving this request.
            available_tool_names: Every tool name currently approved
                and available (post fingerprint check — see
                agent/mcp_client.py) to choose from.

        Returns:
            The curated subset of `available_tool_names` relevant to
            this message. Falls back to returning ALL available tools
            if no category keyword matched — see this method's
            docstring note below on why that's the safer default than
            returning an empty list.

        Design note: falling back to "all tools" rather than "no
        tools" when nothing matches is a deliberate choice — an
        under-curated loadout (a few extra irrelevant tools) is a
        performance/accuracy cost (context confusion, per the module
        docstring); an OVER-curated loadout that excludes the one tool
        actually needed makes the task impossible to complete at all.
        The failure mode of returning too few tools is strictly worse
        than returning too many, so the fallback favors availability.
        """
        message_lower = message.lower()
        matched_categories = [
            category
            for category, keywords in _CATEGORY_KEYWORDS.items()
            if any(re.search(re.escape(keyword), message_lower) for keyword in keywords)
        ]

        if not matched_categories:
            return list(available_tool_names)

        selected: list[str] = []
        for category in matched_categories:
            for tool_name in _CATEGORY_TOOLS[category]:
                if tool_name in available_tool_names and tool_name not in selected:
                    selected.append(tool_name)

        return selected
