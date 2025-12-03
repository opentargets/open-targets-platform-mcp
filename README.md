# OpenTargets MCP

[![Release](https://img.shields.io/github/v/release/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/releases)
[![Build status](https://img.shields.io/github/actions/workflow/status/opentargets/otar-mcp/main.yml?branch=main)](https://github.com/opentargets/otar-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/opentargets/otar-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/opentargets/otar-mcp)
[![Commit activity](https://img.shields.io/github/commit-activity/m/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/commits)
[![License](https://img.shields.io/github/license/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/blob/main/LICENSE)

> **⚠️ DISCLAIMER: This project is currently experimental and under active development. Features, APIs, and documentation may change without notice ⚠️**

**Model Context Protocol (MCP) server for the [OpenTargets Platform API](https://platform.opentargets.org/)**

This package provides an MCP server that enables AI assistants like Claude to interact with the OpenTargets Platform, a comprehensive resource for target-disease associations and drug discovery data.

## Quick Navigation

- [Features](#features)
- [Available Tools](#available-tools)
- [Strategy](#strategy)
- [Usage](#usage)
- [Local Installation](#local-installation)
- [JQ Filtering](#jq-filtering-optional)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔍 **GraphQL Schema Access**: Fetch and explore the complete OpenTargets GraphQL schema with detailed documentation
- 📊 **Query Execution**: Execute custom GraphQL queries against the OpenTargets API
- ⚡ **Batch Query Processing**: Execute the same query multiple times with different parameters efficiently
- 🔎 **Entity Search**: Search for entities across multiple types (targets, diseases, drugs, variants, studies)
- 🚀 **Multiple Transports**: Support for both stdio (Claude Desktop) and HTTP transports
- 🛠️ **CLI Tools**: Easy-to-use command-line interface for server management
- 🎯 **JQ Filtering** (Optional): Server-side JSON filtering to reduce token consumption and improve performance

## Available Tools

The MCP server provides the following tools:

1. **get_open_targets_graphql_schema**: Fetch the complete GraphQL schema for the OpenTargets Platform API, including detailed documentation for all types and fields
2. **query_open_targets_graphql**: Execute GraphQL queries to retrieve data about targets, diseases, drugs, and their associations
3. **batch_query_open_targets_graphql**: Execute the same GraphQL query multiple times with different variable sets for efficient batch processing
4. **search_entity**: Search for entities across multiple types (targets, diseases, drugs, variants, studies) and retrieve their standardized IDs

## Strategy

The MCP server implements a 3-step workflow that guides the LLM to efficiently retrieve data from the OpenTargets Platform:

### Step 1: Learn Query Structure from Schema

The LLM calls `get_open_targets_graphql_schema` to understand the GraphQL API structure. The schema includes detailed documentation for all types and fields, enabling the LLM to construct valid queries. Key entity types include:

- **Targets/Genes**: Use ENSEMBL IDs (e.g., `ENSG00000139618` for BRCA2)
- **Diseases**: Use EFO/MONDO IDs (e.g., `MONDO_0007254` for breast cancer)
- **Drugs**: Use ChEMBL IDs (e.g., `CHEMBL1201583` for aspirin)
- **Variants**: Use "chr_pos_ref_alt" format or rsIDs

### Step 2: Resolve Identifiers (if needed)

When a user query contains common names (gene symbols, disease names, drug names), the LLM uses `search_entity` to convert them to standardized IDs required by the API.

### Step 3: Execute Query

The LLM constructs and executes GraphQL queries using:
- Standardized IDs from Step 2
- Query structure from the schema
- **jq filters** (optional, when enabled) to extract only requested fields, minimizing token consumption

Tool selection:
- `query_open_targets_graphql` for single queries
- `batch_query_open_targets_graphql` for multiple identical queries with different parameters (reduces latency and tokens)

## Usage

### Hosted Service (Recommended)

The easiest way to use OpenTargets MCP is through the hosted service provided by Open Targets infrastructure.

#### Claude Desktop Configuration

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "otar-mcp": {
      "type": "url",
      "url": "https://mcp.platform.opentargets.org/mcp"
    }
  }
}
```

> **Note**: The hosted service uses [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http). The URL above is a placeholder - the actual endpoint will be announced when the service is deployed on Open Targets infrastructure.

### Local Installation

For development, testing, or running your own instance, you can install and run the MCP server locally.

#### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

#### Installation

```bash
git clone https://github.com/opentargets/otar-mcp.git
cd otar-mcp
uv sync
```

#### Claude Desktop Configuration (Local)

```json
{
  "mcpServers": {
    "otar-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/otar-mcp",
        "otar-mcp",
        "serve-stdio"
      ],
      "transport": "stdio"
    }
  }
}
```

To enable jq filtering support (see [JQ Filtering](#jq-filtering-optional) section):

```json
{
  "mcpServers": {
    "otar-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/otar-mcp",
        "otar-mcp",
        "serve-stdio",
        "--jq"
      ],
      "transport": "stdio"
    }
  }
}
```

#### Command Line Usage

```bash
# Start HTTP server (for testing/development)
uv run otar-mcp serve-http
uv run otar-mcp serve-http --host 127.0.0.1 --port 8000
uv run otar-mcp serve-http --jq  # with jq filtering

# Start stdio server
uv run otar-mcp serve-stdio
uv run otar-mcp serve-stdio --jq  # with jq filtering

# List available tools
uv run otar-mcp list-tools
uv run otar-mcp list-tools --jq  # show tools with jq support
```

#### Environment Variables

Configure the server using environment variables:

- `OPENTARGETS_API_ENDPOINT`: OpenTargets API endpoint (default: https://api.platform.opentargets.org/api/v4/graphql)
- `MCP_SERVER_NAME`: Server name (default: "Open Targets MCP")
- `MCP_HTTP_HOST`: HTTP server host (default: "127.0.0.1")
- `MCP_HTTP_PORT`: HTTP server port (default: "8000")
- `OPENTARGETS_TIMEOUT`: Request timeout in seconds (default: "30")
- `OPENTARGETS_JQ_ENABLED`: Enable jq filtering support (default: "false")

### JQ Filtering (Optional)

The MCP server supports optional server-side JSON filtering using jq expressions. This feature is **disabled by default** to simplify the tool interface for most users.

#### When to Enable JQ Filtering

Enable jq filtering when:
- You want to reduce token consumption by extracting only specific fields from API responses
- Working with large API responses where only a subset of data is needed
- The calling LLM is proficient at tool calling and can reliably construct jq filters

Keep jq disabled (default) when:
- Simplicity is preferred over optimization
- Working with straightforward queries that don't benefit from filtering
- The LLM should receive complete API responses

#### Enabling JQ Filtering

**Via CLI flag:**
```bash
otar-mcp serve-stdio --jq
otar-mcp serve-http --jq
```

**Via environment variable:**
```bash
export OPENTARGETS_JQ_ENABLED=true
otar-mcp serve-stdio
```

#### How JQ Filtering Works

When jq filtering is enabled, the query tools expose a `jq_filter` parameter. The jq filter is applied server-side before the response is returned, extracting only the relevant data and discarding unnecessary fields.

Example: To extract only the gene symbol and ID from a target query:
```
jq_filter: ".data.target | {id, symbol: .approvedSymbol}"
```

This significantly reduces token consumption by returning only the requested fields instead of the full API response.

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
otar-mcp/
├── src/otar_mcp/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point for python -m otar_mcp
│   ├── cli.py               # Command-line interface
│   ├── config.py            # Configuration management
│   ├── server.py            # MCP server setup
│   ├── mcp_instance.py      # MCP instance management
│   ├── client/              # GraphQL client utilities
│   │   ├── __init__.py
│   │   └── graphql.py
│   ├── tools/               # MCP tools
│   │   ├── __init__.py
│   │   ├── schema.py        # Schema fetching tool
│   │   ├── query.py         # Query execution tool
│   │   ├── batch_query.py   # Batch query tool
│   │   ├── search.py        # Search tool
│   │   └── register.py      # Conditional tool registration
│   └── utils/               # Utility functions
│       └── __init__.py
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_client/
│   └── test_tools/
└── utils_scripts/           # Utility scripts for maintenance
    └── annotate_schema_metadata.py
```


## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms of the license specified in [LICENSE](LICENSE).

## Acknowledgements

We would like to thank the developers from [@biocontext-ai](https://github.com/biocontext-ai) whose implementation of a GraphQL-based MCP server served as an inspiration for this project.

---

Repository initiated with [fpgmaas/cookiecutter-uv](https://github.com/fpgmaas/cookiecutter-uv).
