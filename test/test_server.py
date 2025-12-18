"""Tests for server module."""

import pytest

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

    @pytest.mark.asyncio
    async def test_all_tools_have_readonly_hint(self):
        """Test that all registered tools have readOnlyHint set to True."""
        server = create_server()
        tools = await server.get_tools()

        # Ensure at least one tool is registered
        assert len(tools) > 0, "No tools registered in the server"

        # Check each tool has readOnlyHint=True
        for tool_name, tool_obj in tools.items():
            assert hasattr(tool_obj, "annotations"), f"Tool '{tool_name}' has no annotations attribute"

            annotations = tool_obj.annotations
            assert hasattr(
                annotations,
                "readOnlyHint",
            ), f"Tool '{tool_name}' annotations have no readOnlyHint attribute"

            assert annotations.readOnlyHint is True, (
                f"Tool '{tool_name}' does not have readOnlyHint=True (got {annotations.readOnlyHint})"
            )


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
