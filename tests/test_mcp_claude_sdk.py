"""Tests for MCP + Claude Agent SDK integration — Sprint 17.

All SDK imports are mocked.
"""

from unittest.mock import patch

import pytest

from pocketclaw.agents.claude_sdk import ClaudeAgentSDK
from pocketclaw.config import Settings
from pocketclaw.mcp.config import MCPServerConfig


class TestClaudeSDKMCPServers:
    """Test _get_mcp_servers method."""

    def _make_sdk(self, **overrides) -> ClaudeAgentSDK:
        """Create a ClaudeAgentSDK with SDK imports mocked out."""
        settings = Settings(
            anthropic_api_key="test-key",
            tool_profile="full",
            **overrides,
        )
        with patch.object(ClaudeAgentSDK, "_initialize"):
            sdk = ClaudeAgentSDK(settings)
            sdk._sdk_available = False  # don't need real SDK
        return sdk

    def test_no_mcp_configs(self):
        sdk = self._make_sdk()
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=[]):
            result = sdk._get_mcp_servers()
        assert result == []

    def test_enabled_stdio_server_passes(self):
        sdk = self._make_sdk()
        cfgs = [
            MCPServerConfig(name="fs", transport="stdio", command="npx", args=["server"]),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert len(result) == 1
        assert result[0]["name"] == "fs"
        assert result[0]["command"] == "npx"

    def test_disabled_server_filtered_out(self):
        sdk = self._make_sdk()
        cfgs = [
            MCPServerConfig(name="fs", transport="stdio", command="npx", enabled=False),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert result == []

    def test_http_server_filtered_out(self):
        """Only stdio servers are supported by Claude SDK."""
        sdk = self._make_sdk()
        cfgs = [
            MCPServerConfig(
                name="remote", transport="http", url="http://localhost:9000"
            ),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert result == []

    def test_policy_denies_server(self):
        sdk = self._make_sdk(tools_deny=["mcp:fs:*"])
        cfgs = [
            MCPServerConfig(name="fs", transport="stdio", command="npx"),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert result == []

    def test_policy_denies_group_mcp(self):
        sdk = self._make_sdk(tools_deny=["group:mcp"])
        cfgs = [
            MCPServerConfig(name="fs", transport="stdio", command="npx"),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert result == []

    def test_env_passed_through(self):
        sdk = self._make_sdk()
        cfgs = [
            MCPServerConfig(
                name="gh",
                transport="stdio",
                command="npx",
                args=["server"],
                env={"GITHUB_TOKEN": "abc"},
            ),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert result[0]["env"] == {"GITHUB_TOKEN": "abc"}

    def test_multiple_servers_mixed(self):
        sdk = self._make_sdk()
        cfgs = [
            MCPServerConfig(name="fs", transport="stdio", command="npx", enabled=True),
            MCPServerConfig(name="off", transport="stdio", command="npx", enabled=False),
            MCPServerConfig(name="web", transport="http", url="http://x"),
        ]
        with patch("pocketclaw.mcp.config.load_mcp_config", return_value=cfgs):
            result = sdk._get_mcp_servers()
        assert len(result) == 1
        assert result[0]["name"] == "fs"

    def test_mcp_import_error_returns_empty(self):
        """If mcp module is not installed, return empty list."""
        sdk = self._make_sdk()
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pocketclaw.mcp" in name:
                raise ImportError("no mcp")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            result = sdk._get_mcp_servers()
        assert result == []
