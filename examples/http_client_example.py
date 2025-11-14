"""Example of using OpenTargets MCP with HTTP transport.

This example demonstrates how to connect to the OpenTargets MCP server
via HTTP transport and call the available tools.
"""

import asyncio

from fastmcp import Client


async def main() -> None:
    """Demonstrate basic usage of OpenTargets MCP tools via HTTP."""
    # Connect to the MCP server
    client = Client("http://localhost:8001/mcp")

    async with client:
        # Example 1: Get example queries
        print("=" * 60)
        print("Example 1: Getting example queries")
        print("=" * 60)
        examples = await client.call_tool("get_open_targets_query_examples")
        print("Examples retrieved successfully!")
        print(f"Response type: {type(examples)}")
        print()

        # Example 2: Get the GraphQL schema (this may take a moment)
        print("=" * 60)
        print("Example 2: Fetching GraphQL schema")
        print("=" * 60)
        schema_result = await client.call_tool("get_open_targets_graphql_schema")
        schema_text = schema_result.content[0].text
        if "error" not in schema_text:
            print(f"Schema fetched successfully! (Length: {len(schema_text)} characters)")
        else:
            print(f"Error: {schema_text}")
        print()

        # Example 3: Execute a simple query
        print("=" * 60)
        print("Example 3: Executing a GraphQL query")
        print("=" * 60)
        query = """
        query getTarget {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
                approvedName
            }
        }
        """
        result = await client.call_tool("query_open_targets_graphql", arguments={"query_string": query})
        print("Query executed successfully!")
        print(f"Response: {result.content[0].text[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
