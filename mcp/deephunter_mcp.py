"""
DeepHunter MCP server (local stdio).

Exposes the DeepHunter REST API (mounted at /api/) as MCP tools so an LLM
client (Claude Desktop, Claude Code, ...) can read and create threat-hunting
analytics conversationally.

This is a thin wrapper: each tool translates a call into an HTTPS request
against the existing REST API, authenticating with a Knox token. No business
logic lives here -- validation, permissions, and side effects (rule sync,
stats regeneration) all happen server-side in DeepHunter.

Design: local stdio. The client launches one process per user, supplying that
user's token via the DEEPHUNTER_API_TOKEN env var, so two users connect with
their own tokens (and their own permissions / created_by attribution).

Auth: obtain a token out-of-band with `python manage.py create_api_token
<username>` on the DeepHunter server, then pass it via DEEPHUNTER_API_TOKEN.
The token's user needs `qm.view_analytic` (read tools) and `qm.add_analytic`
(create_analytic).

Run:
    DEEPHUNTER_API_URL=https://deephunter.se.com/api \
    DEEPHUNTER_API_TOKEN=<token> \
    python deephunter_mcp.py
"""
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

# --- Configuration (from environment) --------------------------------------

BASE_URL = os.environ.get("DEEPHUNTER_API_URL", "https://deephunter.se.com/api")
TOKEN = os.environ.get("DEEPHUNTER_API_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "DEEPHUNTER_API_TOKEN is not set. Generate one on the server with "
        "`python manage.py create_api_token <username>`."
    )

# Verify TLS by default; allow opt-out only for dev boxes with self-signed certs.
VERIFY_TLS = os.environ.get("DEEPHUNTER_VERIFY_TLS", "true").lower() != "false"

mcp = MCPServer(name="deephunter")

client = httpx.Client(
    base_url=BASE_URL.rstrip("/"),
    headers={
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json",
    },
    timeout=30.0,
    verify=VERIFY_TLS,
)


# --- Helpers ---------------------------------------------------------------

def _get(path: str) -> Any:
    """GET a path and return parsed JSON, surfacing API errors as text."""
    return _handle(client.get(path))


def _post(path: str, payload: dict) -> Any:
    return _handle(client.post(path, json=payload))


def _handle(r: httpx.Response) -> Any:
    """Raise a readable error on failure; otherwise return parsed JSON.

    DeepHunter returns DRF-style error bodies (e.g.
    {"connector": ["Object with name=x does not exist."]}); we pass those
    through so the model can correct itself (e.g. call a ref/* tool first).
    """
    if r.is_success:
        return r.json()
    try:
        detail = r.json()
    except ValueError:
        detail = r.text
    raise RuntimeError(f"DeepHunter API {r.status_code}: {detail}")


# --- Reference data (read-only) --------------------------------------------
# These let the model discover valid natural-key values (connector names,
# categories, MITRE IDs, ...) before creating an analytic, avoiding
# validation errors. They require the `qm.view_analytic` permission.

@mcp.tool()
def list_connectors() -> list[dict]:
    """List enabled 'analytics' connectors that can be referenced when
    creating an analytic. Returns [{name, description}]."""
    return _get("/ref/connectors/")


@mcp.tool()
def list_categories() -> list[dict]:
    """List analytic categories. Returns [{name, short_name, description}]."""
    return _get("/ref/categories/")


@mcp.tool()
def list_tags() -> list[dict]:
    """List available tags. Returns [{name}]."""
    return _get("/ref/tags/")


@mcp.tool()
def list_mitre_techniques() -> list[dict]:
    """List MITRE ATT&CK techniques. Reference them by `mitre_id`
    (e.g. 'T1059.001'). Returns [{mitre_id, name, is_subtechnique}]."""
    return _get("/ref/mitre-techniques/")


@mcp.tool()
def list_threats() -> list[dict]:
    """List known threat names. Returns [{name, aka_name}]."""
    return _get("/ref/threats/")


@mcp.tool()
def list_actors() -> list[dict]:
    """List known threat actors. Returns [{name, aka_name}]."""
    return _get("/ref/actors/")


@mcp.tool()
def list_target_os() -> list[dict]:
    """List target operating systems. Returns [{name}]."""
    return _get("/ref/target-os/")


@mcp.tool()
def list_vulnerabilities() -> list[dict]:
    """List vulnerabilities. Reference them by CVE id (e.g. 'CVE-2024-1234').
    Returns [{name, base_score, description}]."""
    return _get("/ref/vulnerabilities/")


# --- Analytics -------------------------------------------------------------

@mcp.tool()
def list_analytics() -> list[dict]:
    """List all analytics. Each item has the same shape as get_analytic."""
    return _get("/analytics/")


@mcp.tool()
def get_analytic(analytic_id: int) -> dict:
    """Retrieve a single analytic by its numeric id. Relations are returned
    as natural keys (connector name, category name, MITRE ids, ...)."""
    return _get(f"/analytics/{analytic_id}/")


@mcp.tool()
def create_analytic(
    name: str,
    connector: str,
    query: str,
    description: str = "",
    status: str = "DRAFT",
    confidence: int | None = None,
    relevance: int | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    mitre_techniques: list[str] | None = None,
    threats: list[str] | None = None,
    actors: list[str] | None = None,
    target_os: list[str] | None = None,
    vulnerabilities: list[str] | None = None,
) -> dict:
    """Create a new analytic.

    Required: name, connector, query.
    - connector: name of an enabled 'analytics' connector (see list_connectors,
      e.g. 'sentinelone').
    - status: only 'DRAFT' or 'PUB' are accepted at creation (default 'DRAFT').
    - Relations (category, tags, mitre_techniques, threats, actors, target_os,
      vulnerabilities) are natural keys and must already exist -- discover valid
      values with the corresponding list_* tools first.

    Requires the `qm.add_analytic` permission. Creating an analytic triggers
    the same server-side behaviour as the web UI (AnalyticMeta creation,
    optional remote rule sync, automatic stats regeneration). Returns the full
    created analytic including its server-assigned id.
    """
    payload: dict[str, Any] = {
        "name": name,
        "connector": connector,
        "query": query,
        "description": description,
        "status": status,
    }
    # Only include optional fields when provided, so the server applies its
    # own defaults otherwise.
    for key, value in (
        ("confidence", confidence),
        ("relevance", relevance),
        ("category", category),
        ("tags", tags),
        ("mitre_techniques", mitre_techniques),
        ("threats", threats),
        ("actors", actors),
        ("target_os", target_os),
        ("vulnerabilities", vulnerabilities),
    ):
        if value is not None:
            payload[key] = value
    return _post("/analytics/", payload)


if __name__ == "__main__":
    # Default stdio transport (suits a local Claude Desktop/Code config).
    mcp.run()
