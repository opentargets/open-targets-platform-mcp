"""Tests for server module."""

from otar_mcp.mcp_instance import mcp
from otar_mcp.server import setup_server


class TestSetupServer:
    """Tests for setup_server function."""

    def test_setup_server_returns_mcp_instance(self):
        """Test that setup_server returns the mcp instance."""
        result = setup_server()

        assert result is not None
        assert result == mcp

    def test_setup_server_imports_tools(self):
        """Test that setup_server imports all tool modules."""
        # Just verify the function runs without errors
        # The actual tool registration is handled by the @mcp.tool decorators
        result = setup_server()

        assert result is not None

    def test_mcp_instance_exists(self):
        """Test that mcp instance is created."""
        from otar_mcp.mcp_instance import mcp

        assert mcp is not None
        # Check it's a FastMCP instance
        assert hasattr(mcp, "tool")  # Should have the tool decorator method


class TestMCPInstance:
    """Tests for MCP instance creation."""

    def test_mcp_instance_is_singleton(self):
        """Test that mcp instance is the same across imports."""
        from otar_mcp.mcp_instance import mcp as mcp1
        from otar_mcp.mcp_instance import mcp as mcp2

        assert mcp1 is mcp2

    def test_mcp_instance_has_required_attributes(self):
        """Test that mcp instance has required FastMCP attributes."""
        from otar_mcp.mcp_instance import mcp

        # FastMCP instances should have these methods
        assert hasattr(mcp, "tool")
        assert callable(mcp.tool)
