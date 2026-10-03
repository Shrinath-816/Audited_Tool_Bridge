"""
agent/safety.py
=================

Hard safety valves for the agent loop — see week-4-notes.md, section 4,
for the full rationale. Reused unchanged from Week 4's design: pure,
dependency-free functions so they're trivially unit-testable in
isolation from the graph itself.
"""


def has_exceeded_max_iterations(iteration_count: int, max_iterations: int) -> bool:
    """Check whether the agent loop has hit its hard iteration cap."""
    return iteration_count >= max_iterations


def is_repeated_tool_call(tool_call_log: list[dict]) -> bool:
    """
    Detect whether the two most recent tool calls are identical (same
    name and arguments) — a strong signal the agent is stuck.

    Args:
        tool_call_log: Ordered history of {"name": ..., "arguments": ...} records.

    Returns:
        True if the last two recorded tool calls are identical.
    """
    if len(tool_call_log) < 2:
        return False
    last, previous = tool_call_log[-1], tool_call_log[-2]
    return last["name"] == previous["name"] and last["arguments"] == previous["arguments"]
