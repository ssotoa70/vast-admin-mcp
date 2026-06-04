#!/usr/bin/env python3
"""Unit tests for HTTP MCP graph links."""

import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path to import vast_admin_mcp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vast_admin_mcp import cli as cli_package
from vast_admin_mcp import mcp_server
from vast_admin_mcp.setup import get_http_server_status

cli = cli_package._cli_module


class TestHttpGraphLinks(unittest.TestCase):
    def test_http_graph_link_replaces_file_uri(self):
        graph_data = {
            "resource_uri": "file:///tmp/performance_graph.png",
            "file_path": "/tmp/performance_graph.png",
        }

        result = mcp_server._add_http_graph_link(graph_data, host="127.0.0.1", port=8000)

        self.assertEqual(result["resource_uri"], "http://127.0.0.1:8000/graphs/performance_graph.png")
        self.assertEqual(result["local_resource_uri"], "file:///tmp/performance_graph.png")
        self.assertEqual(graph_data["resource_uri"], "file:///tmp/performance_graph.png")

    def test_http_graph_link_uses_loopback_for_wildcard_host(self):
        graph_data = {
            "resource_uri": "file:///tmp/performance graph.png",
            "file_path": "/tmp/performance graph.png",
        }

        result = mcp_server._add_http_graph_link(graph_data, host="0.0.0.0", port=8000)

        self.assertEqual(result["resource_uri"], "http://127.0.0.1:8000/graphs/performance%20graph.png")

    @patch.dict(os.environ, {"VAST_ADMIN_MCP_PUBLIC_BASE_URL": "https://vast-mcp.example.com/base/"})
    def test_http_graph_link_uses_public_base_url(self):
        url = mcp_server._build_graph_http_url("graph.png", host="0.0.0.0", port=8000)

        self.assertEqual(url, "https://vast-mcp.example.com/base/graphs/graph.png")

    def test_resolve_graph_file_path_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_file = os.path.join(temp_dir, "graph.png")
            with open(graph_file, "wb") as fh:
                fh.write(b"png")

            with patch.object(mcp_server, "GRAPH_TEMP_DIR", temp_dir):
                self.assertEqual(mcp_server._resolve_graph_file_path("graph.png"), graph_file)
                self.assertIsNone(mcp_server._resolve_graph_file_path("../graph.png"))
                self.assertIsNone(mcp_server._resolve_graph_file_path("missing.png"))


class TestHttpGraphAuthConfig(unittest.TestCase):
    def test_http_status_reports_unauthenticated_graph_links(self):
        status = get_http_server_status({
            "http_server": {
                "enabled": True,
                "port": 8000,
                "disable_output_auth": True,
                "auth": {"type": "bearer"},
            }
        })

        self.assertIn("graph links: unauthenticated", status)

    def test_start_mcp_passes_graph_auth_bypass_to_middleware(self):
        class FakeFastMCP:
            run_kwargs = None

            def __init__(self, *args, **kwargs):
                pass

            def custom_route(self, *args, **kwargs):
                return lambda func: func

            def tool(self, *args, **kwargs):
                return lambda func: func

            def run(self, **kwargs):
                type(self).run_kwargs = kwargs

        with patch.object(mcp_server, "FastMCP", FakeFastMCP):
            mcp_server.start_mcp(
                transport="http",
                auth_config={"type": "bearer", "token": "secret"},
                disable_graph_auth=True,
            )

        middleware = FakeFastMCP.run_kwargs["middleware"][0]
        self.assertTrue(middleware.kwargs["disable_graph_auth"])

    def test_start_mcp_keeps_graph_links_authenticated_by_default(self):
        class FakeFastMCP:
            run_kwargs = None

            def __init__(self, *args, **kwargs):
                pass

            def custom_route(self, *args, **kwargs):
                return lambda func: func

            def tool(self, *args, **kwargs):
                return lambda func: func

            def run(self, **kwargs):
                type(self).run_kwargs = kwargs

        with patch.object(mcp_server, "FastMCP", FakeFastMCP):
            mcp_server.start_mcp(
                transport="http",
                auth_config={"type": "bearer", "token": "secret"},
            )

        middleware = FakeFastMCP.run_kwargs["middleware"][0]
        self.assertFalse(middleware.kwargs["disable_graph_auth"])

    def test_cli_passes_graph_auth_config(self):
        captured = {}
        config_json = """{
            "http_server": {
                "enabled": true,
                "host": "127.0.0.1",
                "port": 8000,
                "path": "/mcp/",
                "disable_output_auth": true,
                "auth": {"type": "none"}
            }
        }"""

        with patch.object(sys, "argv", ["vast-admin-mcp", "mcp", "--transport", "http"]), \
                patch.object(cli, "logging_main", lambda debug=False: None), \
                patch.object(cli.os.path, "isfile", lambda path: path == cli.CONFIG_FILE), \
                patch("builtins.open", lambda *args, **kwargs: StringIO(config_json)), \
                patch.object(cli, "start_mcp", lambda **kwargs: captured.update(kwargs)):
            cli.main()

        self.assertTrue(captured["disable_graph_auth"])


if __name__ == "__main__":
    unittest.main()
