# DeepHunter MCP server (local stdio)

A thin [Model Context Protocol](https://modelcontextprotocol.io/) wrapper around
the DeepHunter REST API. It lets an LLM client (Claude Desktop, Claude Code, …)
read and create threat-hunting analytics conversationally, by exposing the
`/api/` endpoints as MCP tools.

Each tool call becomes an authenticated HTTPS request to the REST API. No logic
lives here — validation, permissions, and side effects (rule sync, stats
regeneration) all happen server-side in DeepHunter.

## Design: local stdio, per-user token

The client launches **one server process per user**, passing that user's Knox
token via an environment variable. Two users therefore connect with their own
tokens — and their own permissions and `created_by` attribution — with no
shared state. The token lives in each user's client config, protected by that
user's filesystem permissions.

## Prerequisites

1. **A token.** On the DeepHunter server, generate one for the user:

   ```bash
   source /data/venv/bin/activate
   python manage.py create_api_token <username> --grant-perms
   ```

   `--grant-perms` grants `qm.view_analytic` (needed by the `list_*` / `get_*`
   tools) and `qm.add_analytic` (needed by `create_analytic`). The plaintext
   token is printed once — copy it.

2. **Python deps on the user's machine** (not the WSGI host):

   ```bash
   pip install -r mcp/requirements.txt
   ```

## Client configuration

Add an `mcpServers` entry to the client config (e.g. Claude Desktop's
`claude_desktop_config.json`). Only the token differs between users:

```json
{
  "mcpServers": {
    "deephunter": {
      "command": "/data/venv/bin/python",
      "args": ["/data/deephunter/mcp/deephunter_mcp.py"],
      "env": {
        "DEEPHUNTER_API_URL": "https://deephunter.se.com/api",
        "DEEPHUNTER_API_TOKEN": "<this user's token>"
      }
    }
  }
}
```

`command` must point to a Python interpreter that has the `mcp` requirements
installed, and `args` to this script's path, on the user's machine.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DEEPHUNTER_API_TOKEN` | yes | — | Knox token from `create_api_token`. |
| `DEEPHUNTER_API_URL` | no | `https://deephunter.se.com/api` | Base URL of the REST API. |
| `DEEPHUNTER_VERIFY_TLS` | no | `true` | Set to `false` only for dev boxes with self-signed certs. |

## Tools

Read-only (need `qm.view_analytic`):

- `list_connectors`, `list_categories`, `list_tags`, `list_mitre_techniques`,
  `list_threats`, `list_actors`, `list_target_os`, `list_vulnerabilities`
- `list_analytics`, `get_analytic(analytic_id)`

Write (needs `qm.add_analytic`):

- `create_analytic(name, connector, query, …)` — `name`, `connector`, and
  `query` are required; relations are natural keys and must already exist
  (discover valid values with the `list_*` tools).

## Example prompts

- "List the DeepHunter connectors."
- "Show me analytic 42."
- "Create a DRAFT analytic named 'Suspicious rundll32 network activity' on the
  sentinelone connector with query …"
