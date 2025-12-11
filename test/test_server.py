"""Tests for server module."""

from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.server import mcp


class TestCreateServer:
    """Tests for create_server function."""

    def test_create_server_returns_mcp_instance(self):
        """Test that create_server returns a FastMCP instance."""
        result = create_server()

        assert result is not None
        # Check it's a FastMCP instance
        assert hasattr(result, "tool")  # Should have the tool decorator method

    def test_create_server_imports_tools(self):
        """Test that create_server imports all tool modules."""
        # Just verify the function runs without errors
        # The actual tool registration is handled by the mcp.tool calls
        result = create_server()

        assert result is not None


class TestMCPInstance:
    """Tests for MCP instance creation."""

    def test_mcp_instance_exists(self):
        """Test that mcp instance is created."""
        assert mcp is not None
        # Check it's a FastMCP instance
        assert hasattr(mcp, "tool")  # Should have the tool decorator method

    def test_mcp_instance_has_required_attributes(self):
        """Test that mcp instance has required FastMCP attributes."""
        # FastMCP instances should have these methods
        assert hasattr(mcp, "tool")
        assert callable(mcp.tool)
