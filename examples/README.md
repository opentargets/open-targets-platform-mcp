# OpenTargets MCP Examples

This directory contains examples of how to use the OpenTargets MCP server.

## HTTP Client Example

See `http_client_example.py` for an example of connecting to the MCP server via HTTP transport.

### Running the HTTP example:

1. Start the HTTP server:
```bash
uv run otar-mcp serve-http
```

2. In another terminal, run the example:
```bash
uv run python examples/http_client_example.py
```

## Stdio Client Example (Claude Desktop)

The stdio transport is the standard way to use MCP servers with Claude Desktop.

### Configuration for Claude Desktop:

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "opentargets": {
      "command": "uv",
      "args": ["run", "otar-mcp", "serve-stdio"],
      "cwd": "/path/to/otar-official-mcp"
    }
  }
}
```

Or if you have installed the package:

```json
{
  "mcpServers": {
    "opentargets": {
      "command": "otar-mcp",
      "args": ["serve-stdio"]
    }
  }
}
```

After configuration, restart Claude Desktop and the tools will be available.

## Available Tools

- **get_open_targets_graphql_schema**: Fetch the complete GraphQL schema
- **query_open_targets_graphql**: Execute GraphQL queries against the OpenTargets API
- **get_open_targets_query_examples**: Get example queries to help you get started
