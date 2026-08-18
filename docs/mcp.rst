MCP server
##########

DeepHunter ships a `Model Context Protocol <https://modelcontextprotocol.io/>`_
(MCP) server that exposes the `REST API <api.html>`_ as tools an LLM client
(Claude Desktop, Claude Code, ...) can call conversationally. It is a thin
wrapper: each tool translates into an authenticated HTTPS request against
``/api/``, so all validation, permissions and side effects happen server-side
in DeepHunter.

The code lives in ``mcp/deephunter_mcp.py``, with its dependencies pinned in
``mcp/requirements.txt``.

Design: local stdio
*******************

The server uses the **local stdio** transport: the MCP client launches one
server process per user, passing that user's Knox token via an environment
variable. Two users therefore connect with their own tokens -- and their own
permissions and ``created_by`` attribution -- with no shared state.

Because the client spawns the process locally, the Python environment and the
dependencies must be installed **on the machine where the MCP client runs**
(this may or may not be the DeepHunter server itself).

Installation
************

1. Generate a token
===================

On the DeepHunter server, generate a Knox token for the user (see the
`REST API documentation <api.html>`_ for details on ``create_api_token``)::

    source /data/venv/bin/activate
    python manage.py create_api_token <username> --grant-perms

``--grant-perms`` grants ``qm.view_analytic`` (needed by the read tools),
``qm.add_analytic`` (needed by ``create_analytic``) and ``qm.view_tag`` /
``qm.add_tag`` (needed by ``create_tag``). The plaintext token is printed once
-- copy it.

2. Create a Python environment
=============================

On the machine that runs the MCP client, create a dedicated virtual environment
in your home directory (kept separate from the DeepHunter ``/data/venv`` so it
does not interfere with the server)::

    python3 -m venv ~/deephunter-mcp-venv

3. Install the dependencies
==========================

Install the MCP server requirements (the MCP SDK and ``httpx``) into that
environment::

    ~/deephunter-mcp-venv/bin/pip install -r /data/deephunter/mcp/requirements.txt

.. note::

   These dependencies (``mcp`` and ``httpx``) are **client-side only**. They are
   intentionally kept out of the project's top-level ``requirements.txt`` so the
   Django/WSGI host does not install packages it never uses. The MCP SDK must be
   version ``2.0.0`` or later (the high-level server class is
   ``mcp.server.mcpserver.MCPServer``).

4. Configure the MCP client
==========================

Add an ``mcpServers`` entry to the client configuration (for Claude Code,
``~/.claude.json``; for Claude Desktop, ``claude_desktop_config.json``). Only
the token differs between users:

.. code-block:: json

    {
      "mcpServers": {
        "deephunter": {
          "command": "/home/<user>/deephunter-mcp-venv/bin/python",
          "args": ["/data/deephunter/mcp/deephunter_mcp.py"],
          "env": {
            "DEEPHUNTER_API_URL": "https://deephunter.domain.tld/api",
            "DEEPHUNTER_API_TOKEN": "<the user's token>"
          }
        }
      }
    }

.. warning::

   Use **absolute paths** for both ``command`` and ``args`` (MCP clients do not
   reliably expand ``~`` or resolve ``$PATH``). ``command`` must point to the
   interpreter of the virtual environment created above -- pointing it at a
   Python that lacks the dependencies, or at a path that does not exist on the
   client machine, results in a spawn failure (``ENOENT``).

Restart / reconnect the client. It should now list the DeepHunter tools.

Environment variables
*********************

============================  ========  =======================================  =====================================================
Variable                      Required  Default                                  Purpose
============================  ========  =======================================  =====================================================
``DEEPHUNTER_API_TOKEN``      yes       --                                       Knox token from ``create_api_token``.
``DEEPHUNTER_API_URL``        no        ``https://deephunter.domain.tld/api``    Base URL of the REST API.
``DEEPHUNTER_VERIFY_TLS``     no        ``true``                                 Set to ``false`` to disable TLS certificate verification.
============================  ========  =======================================  =====================================================

Development servers (self-signed certificates)
**********************************************

If the DeepHunter server presents a self-signed or otherwise untrusted
certificate, tool calls fail with ``SSL: CERTIFICATE_VERIFY_FAILED``. For a
development server, disable certificate verification by adding
``DEEPHUNTER_VERIFY_TLS`` to the ``env`` block:

.. code-block:: json

    "env": {
        "DEEPHUNTER_API_URL": "https://deephunter.domain.tld/api",
        "DEEPHUNTER_API_TOKEN": "<the user's token>",
        "DEEPHUNTER_VERIFY_TLS": "false"
    }

.. warning::

   Disabling verification removes protection against man-in-the-middle attacks
   on the connection. Use it only for development servers, and remove the
   variable (or set it back to ``true``) once a trusted certificate is in place.

Tools
*****

Read-only (require ``qm.view_analytic``):

- ``list_connectors``, ``list_categories``, ``list_tags``,
  ``list_mitre_techniques``, ``list_threats``, ``list_actors``,
  ``list_target_os``, ``list_vulnerabilities``
- ``list_analytics``, ``get_analytic``
- ``get_analytic_status`` -- report whether an analytic's stats run has
  completed (``state`` is ``running`` / ``complete`` / ``never_run``, with a
  ``progress`` percentage) and, once complete, the number of distinct endpoints
  it matched (``distinct_endpoints``). Poll it after ``create_analytic`` to wait
  for the run and learn how prevalent the analytic is.
- ``list_saved_searches`` (requires ``qm.view_savedsearch``) -- list hunting
  packages (saved searches), to discover the exact name to pass to
  ``get_saved_search_endpoints``. **Only saved searches with "public"
  visibility are listed by the MCP service** (plus any created by the token's
  own service account). Private searches owned by other users are not returned;
  to expose one, its owner must mark it public.
- ``get_saved_search_endpoints`` (requires ``qm.view_endpoint``) -- given a
  hunting package name, report how many distinct endpoints match its filters
  (``endpoints_count``) and list them (``endpoints`` with ``hostname``,
  ``site`` and per-endpoint ``analytics_count``).

Write:

- ``create_analytic`` (requires ``qm.add_analytic``) -- ``name``, ``connector``
  and ``query`` are required; relations are natural keys and must already exist
  (discover valid values with the ``list_*`` tools). **Exception:** any ``tags``
  that do not yet exist are created automatically before the analytic is saved
  (this needs ``qm.add_tag``), so an unknown tag never fails the call. All other
  relations must already exist.
- ``create_tag`` (requires ``qm.add_tag``) -- explicitly create a tag by name.
  Usually not needed, since ``create_analytic`` auto-creates missing tags; use
  it to create a tag on its own.

Example prompts
***************

Once the server is connected, you interact with it in plain language: you do
**not** call tools by name. Describe what you want and the LLM client selects
the appropriate tool(s). A few examples:

Discover reference values and list analytics::

    "Which connectors can I use in DeepHunter?"
    "List all analytics."
    "Show me analytic 42."

Create an analytic (the client resolves relations via the ``list_*`` tools and
calls ``create_analytic``)::

    "Create a DeepHunter analytic named 'Suspicious rundll32 network activity'
     for the sentinelone connector that detects rundll32.exe making network
     connections. Tag it 'lolbin' and 'network', and map it to T1218.011."

Check an analytic's run status and its distinct-endpoint count
(``get_analytic_status``)::

    "Has analytic 42 finished running? If so, how many distinct endpoints did
     it match?"
    "What's the status of the analytic I just created?"

Query a hunting package / saved search (``list_saved_searches`` then
``get_saved_search_endpoints``)::

    "Which hunting packages are available?"
    "How many endpoints match the 'Emotet hunting' package, and list them."
    "For the saved search named 'Ransomware TTPs', how many distinct endpoints
     are affected and which hosts are they?"

Chain creation and status in one request (the client creates the analytic, then
polls ``get_analytic_status`` until the run completes)::

    "Create an analytic for rundll32 network connections, then wait until it
     finishes running and tell me how many endpoints it matched."

.. note::

   The client polls ``get_analytic_status`` by calling it again; it does not
   refresh on its own between your messages. If a run is still ``running``, ask
   it to "check again" and it will re-poll.
