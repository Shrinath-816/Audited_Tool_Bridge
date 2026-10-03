# The Audited Tool Bridge — 

Legacy enterprise APIs (order lookup, refunds, support tickets)
exposed as a standardized, secure MCP server — with a client-side
defense against MCP's documented "rug pull" attack (a tool silently
redefined after approval), server-side audit logging of every
invocation, and a context-engineering-driven, per-request tool loadout
that curates which tools are even offered to the model, instead of
always binding the full catalog.

This is Week 6 of a 10-week self-study AI Engineering program, built
on the agent-loop pattern from Week 4. See `week-6-notes.md` (provided
separately) for the concept notes this project implements.

## What this project demonstrates

| Concept | Where it lives |
|---|---|
| Custom MCP server (Tools + Resource) | `mcp_server/server.py`, wrapping `mcp_server/backend.py` |
| Server-side audit logging | `mcp_server/audit_log.py` |
| MCP client, raw + LangChain-adapted | `agent/mcp_client.py` |
| Rug-pull defense (tool fingerprinting) | `agent/fingerprint_registry.py`, enforced in `agent/mcp_client.py` |
| Context engineering "select" lever (curated tool loadout) | `agent/loadout_selector.py` |
| Agent loop (Week 4 pattern, now over MCP tools) | `agent/graph.py` |

## Project structure

```
audited-tool-bridge/
├── mcp_server/                     # THE MCP SERVER (run this first)
│   ├── __init__.py
│   ├── backend.py                   # Simulated legacy system (orders, tickets)
│   ├── audit_log.py                 # Server-side audit trail
│   └── server.py                    # FastMCP: tools, resource, audit-log tool
├── agent/                          # THE AGENT SERVICE (connects to the above)
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py                   # HTTP API request/response models
│   ├── state.py                     # LangGraph state schema
│   ├── safety.py                    # Agent loop safety valves (Week 4 pattern)
│   ├── llm.py                       # ChatOpenRouter construction (tools NOT pre-bound)
│   ├── fingerprint_registry.py      # Rug-pull defense
│   ├── mcp_client.py                # Discovery + fingerprint check + LangChain wrapping
│   ├── loadout_selector.py          # Per-request curated tool subset
│   ├── graph.py                     # The agent loop over curated MCP tools
│   └── main.py                      # FastAPI app: POST /chat
├── tests/
│   ├── test_backend.py
│   ├── test_audit_log.py
│   ├── test_fingerprint_registry.py
│   ├── test_loadout_selector.py
│   └── test_graph_routing.py
├── requirements.txt
├── pytest.ini
├── Dockerfile.mcp_server
├── Dockerfile.agent
├── docker-compose.yml
├── .env.example
└── README.md
```

## Setup

1. **Get an OpenRouter API key**: https://openrouter.ai/keys
2. **Check current model availability** at https://openrouter.ai/models — `CHAT_MODEL` in `.env.example` is a placeholder and must support tool calling.
3. **Create your environment file:**
   ```bash
   cp .env.example .env
   # edit .env: paste your real OPENROUTER_API_KEY
   ```
4. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Start the MCP server FIRST** (in its own terminal):
   ```bash
   python -m mcp_server.server
   ```
   This runs on `http://localhost:8765/mcp` by default (Streamable HTTP — see week-6-notes.md section 2 on why this transport for a shared/remote server rather than stdio).
6. **Start the agent service** (in a second terminal):
   ```bash
   uvicorn agent.main:app --reload
   ```

## Usage

### A simple order lookup (curated loadout: order tools only)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the status of order ORD-1001?"}'
```
The response's `tool_calls` should show only `get_order_status` was used — `loadout_selector.py` curated the toolset to order-related tools for this message, per week-6-notes.md section 6's "select" lever.

### A dependent, multi-tool refund flow
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "My order ORD-1003 arrived broken, please refund it."}'
```
Watch the agent call `get_order_status` before `issue_refund` — the model decides this order itself; the tools are just discovered from MCP.

### Watch the rug-pull defense actually fire
1. Send any request once (this auto-approves all current tool fingerprints).
2. Edit `mcp_server/server.py`: change `issue_refund`'s docstring to something different.
3. Restart the MCP server, then send another `/chat` request.
4. The response's `flagged_tools` field should now list `issue_refund` as changed since approval — and the agent will NOT have access to it (verify by asking for a refund; it can no longer do so with that tool excluded).

### Inspect the server-side audit trail
The server exposes `get_audit_log` as a tool — ask the agent directly:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the recent audit log."}'
```
(Or read `audit_log.jsonl`, written alongside wherever you ran the MCP server from.)

### Health check
```bash
curl http://localhost:8000/health
```

## Running with Docker

```bash
docker compose up --build
```
Update `.env`'s `MCP_SERVER_URL` to `http://mcp_server:8765/mcp` first (service-to-service DNS, not `localhost`, inside compose — see `docker-compose.yml`'s comment).

## Running tests

```bash
pytest
```
All tests are pure logic — no running MCP server, no network, no LLM calls needed. `test_fingerprint_registry.py` specifically exercises the rug-pull detection scenario described above, deterministically.

## Definition of Done (Week 6 milestone)

- [x] The agent completes a task using tools loaded entirely through MCP discovery, not local function calls
- [x] Editing a tool's description on the server and restarting it causes that tool to be excluded from the agent's toolset until re-approved (a demonstrated rug-pull defense)
- [x] Every tool invocation produces a corresponding server-side audit log entry, independent of the agent's own `tool_call_log`
- [x] The loadout selector demonstrably binds a different tool subset for at least two distinct message categories

## Known limitations (intentional — addressed in later weeks / noted extensions)

- No OAuth 2.1 authentication on the Streamable HTTP server — it runs unauthenticated for local development; required before any real remote deployment (week-6-notes.md section 5).
- `get_audit_log` is exposed alongside general-purpose tools rather than behind a separately-scoped, privileged server — see `server.py`'s docstring note on scoping this down in production.
- Only one MCP server exists in this project, so tool-shadowing/cross-server isolation (week-6-notes.md section 5) isn't exercised here — relevant once a second, lower-trust server is introduced.
- The fingerprint registry is in-memory only (resets on agent restart) — a production version would persist approvals durably; see `fingerprint_registry.py`'s docstring for that extension point.
- This project intentionally does NOT re-implement Week 4/5's customer memory system — its scope is the MCP bridge itself (discovery, fingerprinting, auditing, curated loadouts), not a full-featured support agent.
