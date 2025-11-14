# OpenTargets MCP

[![Release](https://img.shields.io/github/v/release/fcarli/otar-mcp)](https://img.shields.io/github/v/release/fcarli/otar-mcp)
[![Build status](https://img.shields.io/github/actions/workflow/status/fcarli/otar-mcp/main.yml?branch=main)](https://github.com/fcarli/otar-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/fcarli/otar-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/fcarli/otar-mcp)
[![Commit activity](https://img.shields.io/github/commit-activity/m/fcarli/otar-mcp)](https://img.shields.io/github/commit-activity/m/fcarli/otar-mcp)
[![License](https://img.shields.io/github/license/fcarli/otar-mcp)](https://img.shields.io/github/license/fcarli/otar-mcp)

**Model Context Protocol (MCP) server for the [OpenTargets Platform API](https://platform.opentargets.org/)**

This package provides an MCP server that enables AI assistants like Claude to interact with the OpenTargets Platform, a comprehensive resource for target-disease associations and drug discovery data.

- **Github repository**: <https://github.com/fcarli/otar-mcp/>
- **Documentation**: <https://fcarli.github.io/otar-mcp/>

## Features

- 🔍 **GraphQL Schema Access**: Fetch and explore the complete OpenTargets GraphQL schema
- 📊 **Query Execution**: Execute custom GraphQL queries against the OpenTargets API
- 📚 **Example Queries**: Access pre-built query examples for common use cases
- 🚀 **Multiple Transports**: Support for both stdio (Claude Desktop) and HTTP transports
- 🛠️ **CLI Tools**: Easy-to-use command-line interface for server management

## Available Tools

The MCP server provides the following tools:

1. **get_open_targets_graphql_schema**: Fetch the complete GraphQL schema for the OpenTargets Platform API
2. **query_open_targets_graphql**: Execute GraphQL queries to retrieve data about targets, diseases, drugs, and their associations
3. **get_open_targets_query_examples**: Get pre-built example queries to help you get started

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/fcarli/otar-mcp.git
cd otar-mcp
uv sync
```

### Using pip

```bash
pip install git+https://github.com/fcarli/otar-mcp.git
```

## Usage

### Claude Desktop Integration (Stdio Transport)

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "opentargets": {
      "command": "uv",
      "args": ["run", "otar-mcp", "serve-stdio"],
      "cwd": "/path/to/otar-mcp"
    }
  }
}
```

Or if installed via pip:

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

### Command Line Usage

#### Start HTTP server (for testing/development)

```bash
# Using uv
uv run otar-mcp serve-http

# Using installed package
otar-mcp serve-http --host 127.0.0.1 --port 8000
```

#### Start stdio server

```bash
# Using uv
uv run otar-mcp serve-stdio

# Using installed package
otar-mcp serve-stdio
```

#### List available tools

```bash
uv run otar-mcp list-tools
```

#### Run as a Python module

```bash
python -m otar_mcp serve-http
```

### Environment Variables

Configure the server using environment variables:

- `OPENTARGETS_API_ENDPOINT`: OpenTargets API endpoint (default: https://api.platform.opentargets.org/api/v4/graphql)
- `MCP_SERVER_NAME`: Server name (default: "Open Targets MCP")
- `MCP_HTTP_HOST`: HTTP server host (default: "127.0.0.1")
- `MCP_HTTP_PORT`: HTTP server port (default: "8000")
- `OPENTARGETS_TIMEOUT`: Request timeout in seconds (default: "30")

### Examples

See the [examples](./examples/) directory for usage examples:

- `http_client_example.py`: Connect to the MCP server via HTTP
- `stdio_client_example.py`: Information about stdio transport configuration
- `README.md`: Detailed examples and configuration

## Development

### Setup development environment

```bash
make install
```

This will install the package with development dependencies and set up pre-commit hooks.

### Run tests

```bash
uv run pytest
```

### Run linting

```bash
uv run pre-commit run -a
```

### Project Structure

```
src/otar_mcp/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point for python -m otar_mcp
├── cli.py               # Command-line interface
├── config.py            # Configuration management
├── server.py            # MCP server setup
├── client/              # GraphQL client utilities
│   ├── __init__.py
│   └── graphql.py
├── tools/               # MCP tools
│   ├── __init__.py
│   ├── schema.py        # Schema fetching tool
│   ├── query.py         # Query execution tool
│   └── examples.py      # Example queries tool
└── utils/               # Utility functions
    └── __init__.py
```

## OpenTargets Platform

The OpenTargets Platform is an open-source resource that provides evidence on target-disease associations. It integrates data from multiple sources to help researchers:

- Identify and prioritize drug targets
- Understand disease mechanisms
- Explore drug-target-disease relationships
- Access genetic and genomic evidence

For more information, visit [platform.opentargets.org](https://platform.opentargets.org/)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms of the license specified in [LICENSE](LICENSE).

---

Repository initiated with [fpgmaas/cookiecutter-uv](https://github.com/fpgmaas/cookiecutter-uv).
