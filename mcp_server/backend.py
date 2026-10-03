"""
mcp_server/backend.py
========================

Stand-ins for what would be real legacy enterprise systems in
production (an order management database, a ticketing system) — see
week-6-notes.md's framing of this project: "wrap internal systems into
heavily audited tools." Mutating these in-memory dicts is what makes
`issue_refund`/`create_support_ticket` real actions with visible side
effects, the same pattern as Week 4's tools.py.

Kept completely separate from server.py (the MCP-facing layer) so the
"legacy system" logic has no MCP-specific concerns mixed into it — in
a real migration, this file's role would be played by an actual legacy
API client, and only server.py would need to change.
"""

_ORDERS: dict[str, dict] = {
    "ORD-1001": {"status": "delivered", "total": 89.99, "refunded": False},
    "ORD-1002": {"status": "processing", "total": 34.50, "refunded": False},
    "ORD-1003": {"status": "delivered", "total": 210.00, "refunded": False},
}

_SUPPORT_TICKETS: list[dict] = []

REFUND_POLICY_TEXT = (
    "Refunds are issued within 30 days of purchase for any order not marked as final "
    "sale. Orders must be looked up and confirmed as eligible before a refund is issued."
)


def get_order_status(order_id: str) -> str:
    """Look up an order's current status, total, and refund state."""
    order = _ORDERS.get(order_id)
    if order is None:
        return f"No order found with ID '{order_id}'."
    return (
        f"Order {order_id}: status={order['status']}, total=${order['total']:.2f}, "
        f"refunded={order['refunded']}"
    )


def issue_refund(order_id: str, reason: str) -> str:
    """Issue a refund for an order — a real, side-effecting action."""
    order = _ORDERS.get(order_id)
    if order is None:
        return f"Cannot issue refund: no order found with ID '{order_id}'."
    if order["refunded"]:
        return f"Order {order_id} has already been refunded."
    order["refunded"] = True
    return f"Refund of ${order['total']:.2f} issued for order {order_id}. Reason recorded: {reason}"


def create_support_ticket(summary: str, priority: str = "normal") -> str:
    """Create a support ticket for follow-up."""
    ticket_id = f"TCK-{len(_SUPPORT_TICKETS) + 1:04d}"
    _SUPPORT_TICKETS.append({"id": ticket_id, "summary": summary, "priority": priority})
    return f"Support ticket {ticket_id} created (priority={priority})."


def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression (no eval() — see the AST walker below)."""
    import ast
    import operator as op

    allowed_operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.USub: op.neg,
    }

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_operators:
            return allowed_operators[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_operators:
            return allowed_operators[type(node.op)](_eval_node(node.operand))
        raise ValueError(f"Unsupported expression element: {ast.dump(node)}")

    try:
        return str(_eval_node(ast.parse(expression, mode="eval").body))
    except Exception as exc:
        return f"Could not evaluate '{expression}': {exc}"
