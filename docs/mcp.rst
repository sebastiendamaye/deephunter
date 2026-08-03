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

``--grant-perms`` grants ``qm.view_analytic`` (needed by the read tools) and
``qm.add_analytic`` (needed by ``create_analytic``). The plaintext token is
printed once -- copy it.

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

Write (requires ``qm.add_analytic``):

- ``create_analytic`` -- ``name``, ``connector`` and ``query`` are required;
  relations are natural keys and must already exist (discover valid values with
  the ``list_*`` tools).
