"""Conditional tool registration for OpenTargets MCP server."""

from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


def register_query_tools() -> None:
    """Register query tools based on jq_enabled configuration.

    This function should be called once during server setup,
    after config.jq_enabled has been set.
    """
    if config.jq_enabled:
        _register_with_jq()
    else:
        _register_without_jq()


def _register_with_jq() -> None:
    """Register tools with jq filter support."""
    from otar_mcp.tools.batch_query import (
        DOCSTRING_WITH_JQ as BATCH_DOCSTRING_WITH_JQ,
    )
    from otar_mcp.tools.batch_query import (
        batch_query_with_jq,
    )
    from otar_mcp.tools.query import DOCSTRING_WITH_JQ, query_with_jq

    # Set docstrings before registration
    query_with_jq.__doc__ = DOCSTRING_WITH_JQ
    batch_query_with_jq.__doc__ = BATCH_DOCSTRING_WITH_JQ

    # Register with FastMCP using the tool decorator as a function
    mcp.tool(name="query_open_targets_graphql")(query_with_jq)
    mcp.tool(name="batch_query_open_targets_graphql")(batch_query_with_jq)


def _register_without_jq() -> None:
    """Register tools without jq filter support."""
    from otar_mcp.tools.batch_query import (
        DOCSTRING_WITHOUT_JQ as BATCH_DOCSTRING_WITHOUT_JQ,
    )
    from otar_mcp.tools.batch_query import (
        batch_query_without_jq,
    )
    from otar_mcp.tools.query import DOCSTRING_WITHOUT_JQ, query_without_jq

    # Set docstrings before registration
    query_without_jq.__doc__ = DOCSTRING_WITHOUT_JQ
    batch_query_without_jq.__doc__ = BATCH_DOCSTRING_WITHOUT_JQ

    # Register with FastMCP using the tool decorator as a function
    mcp.tool(name="query_open_targets_graphql")(query_without_jq)
    mcp.tool(name="batch_query_open_targets_graphql")(batch_query_without_jq)
