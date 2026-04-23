"""Tests for server module."""

import pytest

from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.server import mcp
from open_targets_platform_mcp.tools.schema.schema import build_schema_docstring


class TestCreateServer:
    """Tests for create_server function."""

    @pytest.mark.asyncio
    async def test_create_server_returns_mcp_instance(self):
        """Test that create_server returns a FastMCP instance."""
        result = await create_server()

        assert result is not None
        # Check it's a FastMCP instance
        assert hasattr(result, "tool")  # Should have the tool decorator method

    @pytest.mark.asyncio
    async def test_create_server_imports_tools(self):
        """Test that create_server imports all tool modules."""
        # Just verify the function runs without errors
        # The actual tool registration is handled by the mcp.tool calls
        result = await create_server()

        assert result is not None

    @pytest.mark.asyncio
    async def test_schema_tool_description_is_full_docstring(self):
        """The registered get_open_targets_graphql_schema description must include
        the full category list, regardless of FastMCP version.

        Regression: FastMCP 3.x parses Google-style docstrings via griffe and only
        keeps the first text section, dropping the trailing "Available categories:"
        block. Passing description= explicitly to mcp.tool(...) bypasses that.
        """
        server = await create_server()
        tool = await server.get_tool("get_open_targets_graphql_schema")

        assert tool.description is not None
        assert tool.description.rstrip() == build_schema_docstring().rstrip()
        assert "Available categories:" in tool.description
        assert "drug-mechanisms" in tool.description
        assert "genetic-associations" in tool.description

    @pytest.mark.asyncio
    async def test_type_dependencies_tool_description_is_full(self):
        """The registered get_type_dependencies description must include the
        Examples block and the dict-shape explanation, regardless of FastMCP
        version. Same griffe-truncation regression as above."""
        server = await create_server()
        tool = await server.get_tool("get_type_dependencies")

        assert tool.description is not None
        assert "Examples:" in tool.description
        assert 'get_type_dependencies(["Target"])' in tool.description
        assert "shared" in tool.description

    @pytest.mark.asyncio
    async def test_all_tools_have_readonly_hint(self):
        """Test that all registered tools have readOnlyHint set to True."""
        server = await create_server()

        # FastMCP 2.x exposes get_tools() returning a dict; 3.x exposes list_tools()
        # returning a list.
        if hasattr(server, "get_tools"):
            tools = list((await server.get_tools()).values())
        else:
            tools = await server.list_tools()

        assert len(tools) > 0, "No tools registered in the server"

        for tool_obj in tools:
            assert hasattr(tool_obj, "annotations"), f"Tool '{tool_obj.name}' has no annotations attribute"

            annotations = tool_obj.annotations
            assert hasattr(
                annotations,
                "readOnlyHint",
            ), f"Tool '{tool_obj.name}' annotations have no readOnlyHint attribute"

            assert annotations.readOnlyHint is True, (
                f"Tool '{tool_obj.name}' does not have readOnlyHint=True (got {annotations.readOnlyHint})"
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
