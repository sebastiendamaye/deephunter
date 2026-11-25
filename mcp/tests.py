import os
import unittest
from unittest import mock

os.environ.setdefault("DEEPHUNTER_API_TOKEN", "test-token")

import mcp.deephunter_mcp as mcp_module


class AnalyticReferenceSerializationTests(unittest.TestCase):
    def test_create_analytic_serializes_references_to_newlines(self):
        with mock.patch.object(mcp_module, "_post", return_value={"ok": True}) as mock_post:
            mcp_module.create_analytic(
                name="Test analytic",
                connector="sentinelone",
                query="src.process.name = 'cmd.exe'",
                references=["https://example.com/one", "https://example.com/two"],
            )

        self.assertEqual(
            mock_post.call_args[0][1]["references"],
            "https://example.com/one\nhttps://example.com/two",
        )

    def test_update_analytic_serializes_references_to_newlines(self):
        with mock.patch.object(mcp_module, "_patch", return_value={"ok": True}) as mock_patch:
            mcp_module.update_analytic(
                analytic_id=42,
                references=["https://example.com/one", "https://example.com/two"],
            )

        self.assertEqual(
            mock_patch.call_args[0][1]["references"],
            "https://example.com/one\nhttps://example.com/two",
        )
