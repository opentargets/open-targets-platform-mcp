"""Tool for fetching the OpenTargets GraphQL schema."""

from importlib import resources


def get_open_targets_graphql_schema() -> str:
    """Retrieve the Open Targets Platform GraphQL schema.

    Returns:
        str: the schema text.
    """
    return resources.files("open_targets_platform_mcp.tools.schema").joinpath("schema.txt").read_text(encoding="utf-8")
