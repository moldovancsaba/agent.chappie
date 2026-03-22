from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.tools import ToolRegistry, fetch_url
from agent_chappie.workflows import WorkflowOptions, run_article_summary_workflow


class ToolTests(unittest.TestCase):
    @patch("agent_chappie.tools.urlopen")
    def test_fetch_url_truncates_response(self, mock_urlopen) -> None:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = b"abcdef"

        content = fetch_url("https://example.com", char_limit=3)
        self.assertEqual(content, "abc")

    def test_registry_rejects_unknown_tool(self) -> None:
        registry = ToolRegistry(fetcher=lambda _: "unused")
        with self.assertRaises(ValueError):
            registry.execute("bad_tool", "https://example.com")

    def test_dry_run_workflow_is_repeatable(self) -> None:
        result = run_article_summary_workflow(
            WorkflowOptions(
                task="Fetch and summarise an article",
                url="https://example.com",
                dry_run=True,
            )
        )
        self.assertEqual(result["output"]["status"], "complete")
        self.assertEqual(result["run_mode"], "dry-run")
        self.assertEqual(result["artifacts"]["decision_record"]["decision"], "proceed")


if __name__ == "__main__":
    unittest.main()
