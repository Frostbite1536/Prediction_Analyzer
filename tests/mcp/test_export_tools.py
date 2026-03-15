# tests/mcp/test_export_tools.py
"""Tests for MCP export tools."""

import json
import asyncio
import os
import tempfile


from prediction_mcp.tools import export_tools


class TestExportTrades:
    def test_no_trades_error(self):
        result = asyncio.run(
            export_tools.handle_tool(
                "export_trades",
                {
                    "format": "csv",
                    "output_path": "/tmp/test.csv",
                },
            )
        )
        assert "No trades loaded" in result[0].text

    def test_missing_format(self, loaded_session):
        result = asyncio.run(
            export_tools.handle_tool(
                "export_trades",
                {
                    "output_path": "/tmp/test.csv",
                },
            )
        )
        assert "format is required" in result[0].text

    def test_missing_output_path(self, loaded_session):
        result = asyncio.run(
            export_tools.handle_tool(
                "export_trades",
                {
                    "format": "csv",
                },
            )
        )
        assert "output_path is required" in result[0].text

    def test_export_csv(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name

        try:
            result = asyncio.run(
                export_tools.handle_tool(
                    "export_trades",
                    {
                        "format": "csv",
                        "output_path": path,
                    },
                )
            )
            data = json.loads(result[0].text)
            assert data["trade_count"] == 10
            assert data["format"] == "csv"
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_export_json(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            result = asyncio.run(
                export_tools.handle_tool(
                    "export_trades",
                    {
                        "format": "json",
                        "output_path": path,
                    },
                )
            )
            data = json.loads(result[0].text)
            assert data["trade_count"] == 10
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_invalid_format(self, loaded_session):
        result = asyncio.run(
            export_tools.handle_tool(
                "export_trades",
                {
                    "format": "pdf",
                    "output_path": "/tmp/test.pdf",
                },
            )
        )
        assert "Invalid export format" in result[0].text
