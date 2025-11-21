# OpenTargets MCP

[![Release](https://img.shields.io/github/v/release/opentargets/otar-mcp)](https://img.shields.io/github/v/release/opentargets/otar-mcp)
[![Build status](https://img.shields.io/github/actions/workflow/status/opentargets/otar-mcp/main.yml?branch=main)](https://github.com/opentargets/otar-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/opentargets/otar-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/opentargets/otar-mcp)
[![Commit activity](https://img.shields.io/github/commit-activity/m/opentargets/otar-mcp)](https://img.shields.io/github/commit-activity/m/opentargets/otar-mcp)
[![License](https://img.shields.io/github/license/opentargets/otar-mcp)](https://img.shields.io/github/license/opentargets/otar-mcp)

**Model Context Protocol (MCP) server for the [OpenTargets Platform API](https://platform.opentargets.org/)**

This package provides an MCP server that enables AI assistants like Claude to interact with the OpenTargets Platform, a comprehensive resource for target-disease associations and drug discovery data.

- **Github repository**: <https://github.com/opentargets/otar-mcp/>

## Features

- 🔍 **GraphQL Schema Access**: Fetch and explore the complete OpenTargets GraphQL schema
- 📊 **Query Execution**: Execute custom GraphQL queries against the OpenTargets API
- ⚡ **Batch Query Processing**: Execute the same query multiple times with different parameters efficiently
- 🔎 **Entity Search**: Convert common names (gene symbols, disease names, drug names) to standardized IDs
- 📚 **Curated Query Examples**: Access 150+ pre-built query examples organized by category
- 🚀 **Multiple Transports**: Support for both stdio (Claude Desktop) and HTTP transports
- 🛠️ **CLI Tools**: Easy-to-use command-line interface for server management
- 🎯 **JQ Filtering**: Server-side JSON filtering to reduce token consumption and improve performance

## Strategy

The MCP server implements a 4-step workflow that guides the LLM to efficiently retrieve data from the OpenTargets Platform:

### Step 1: Resolve Identifiers

When a user query contains common names (gene symbols, disease names, drug names), the LLM is guided to use the `search_entity` tool to convert them to standardized IDs required by the API:

- **Targets/Genes**: "BRCA2" → ENSEMBL ID `ENSG00000139618`
- **Diseases**: "breast cancer" → EFO/MONDO ID `MONDO_0007254`
- **Drugs**: "aspirin" → ChEMBL ID `CHEMBL1201583`
- **Variants**: "chr_pos_ref_alt" format or rsIDs

### Step 2: Learn Query Structure

The LLM calls `get_open_targets_query_examples` with relevant categories to understand proper GraphQL syntax, available fields, and query structure. Examples serve as templates for constructing queries.

If examples are insufficient or query errors occur, `get_open_targets_graphql_schema` provides complete type definitions (note: this is token-expensive and should only be used when necessary).

### Step 3: Construct Query with JQ Filter

The LLM builds GraphQL queries using:
- Standardized IDs from Step 1
- Query patterns from Step 2
- **jq filters** to extract only requested fields, minimizing token consumption

The jq filter is applied server-side before returning the response, ensuring only relevant data is transmitted.

### Step 4: Execute

The LLM executes the query with appropriate tool selection:
- `query_open_targets_graphql` for single queries
- `batch_query_open_targets_graphql` for multiple identical queries with different parameters (reduces latency and tokens)



## Available Tools

The MCP server provides the following tools:

1. **get_open_targets_graphql_schema**: Fetch the complete GraphQL schema for the OpenTargets Platform API
2. **query_open_targets_graphql**: Execute GraphQL queries to retrieve data about targets, diseases, drugs, and their associations
3. **batch_query_open_targets_graphql**: Execute the same GraphQL query multiple times with different variable sets for efficient batch processing
4. **search_entity**: Search for entities across multiple types (targets, diseases, drugs, variants, studies) and convert common names to standardized IDs
5. **get_open_targets_query_examples**: Get pre-built example queries organized by category to help the agent in formulating required GraphQL queries

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/opentargets/otar-mcp.git
cd otar-mcp
uv sync
```

### Using pip

```bash
pip install git+https://github.com/opentargets/otar-mcp.git
```

## Usage

### Claude Desktop Integration (Stdio Transport)

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "otar-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/otar-mcp",
        "fastmcp",
        "run",
        "src/otar_mcp/server.py"
      ],
      "transport": "stdio",
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
│   │   ├── examples.py      # Example queries tool
│   │   ├── search.py        # Search tool
│   │   ├── search_entity.py # Entity search tool
│   │   └── semantic_search.py # Semantic search tool
│   └── utils/               # Utility functions
│       └── __init__.py
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_client/
│   └── test_tools/
├── extracted_queries/       # Pre-extracted GraphQL queries
│   ├── credibleset/
│   ├── disease/
│   ├── drug/
│   ├── evidence/
│   ├── search/
│   ├── study/
│   ├── target/
│   ├── variant/
│   ├── queries_catalog.csv
│   ├── query_embeddings.npy
│   └── schema.graphql
├── mappers/                 # Category and query mapping files
│   ├── category_descriptors.json
│   ├── category_query_mapper.json
│   └── query_category_mapper.json
└── utils_scripts/           # Utility scripts for maintenance
    ├── annotate_schema_metadata.py
    └── sync_queries_catalog.py
```


## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms of the license specified in [LICENSE](LICENSE).

---

Repository initiated with [fpgmaas/cookiecutter-uv](https://github.com/fpgmaas/cookiecutter-uv).
