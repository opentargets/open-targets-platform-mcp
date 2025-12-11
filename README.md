# Open Targets Platform MCP

[![Commit activity](https://img.shields.io/github/commit-activity/m/opentargets/open-targets-platform-mcp)](https://github.com/opentargets/open-targets-platform-mcp/commits)
[![License](https://img.shields.io/github/license/opentargets/open-targets-platform-mcp)](https://github.com/opentargets/open-targets-platform-mcp/blob/main/LICENSE)

> **⚠️ DISCLAIMER: This project is currently experimental and under active development. Features, APIs, and documentation may change without notice ⚠️**

**Model Context Protocol (MCP) server for the [OpenTargets Platform API](https://platform.opentargets.org/)**

This package provides an MCP server that enables AI assistants like Claude to interact with the Open Targets Platform API, a comprehensive resource for target-disease associations and drug discovery data.

## Quick Navigation

- [Features](#features)
- [Official MCP Server](#official-mcp-server)
- [Local Deployment](#local-deployment)
- [Advanced Deployment](#advanced-deployment)
- [Available Tools](#available-tools)
- [Strategy](#strategy)
- [Usage](#usage)
- [JQ Filtering](#jq-filtering-optional)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔍 **GraphQL Schema Access**: Fetch and explore the complete OpenTargets GraphQL schema with detailed documentation
- 📊 **Query Execution**: Execute custom GraphQL queries against the OpenTargets API
- ⚡ **Batch Query Processing**: Execute the same query multiple times with different parameters efficiently
- 🔎 **Entity Search**: Search for entities across multiple types (targets, diseases, drugs, variants, studies)
- 🛠️ **CLI Tools**: Easy-to-use command-line interface for server management
- 🎯 **JQ Filtering** (Optional): Server-side JSON filtering using [jq](https://jqlang.org/) to reduce token consumption and improve performance

## Official MCP Server

The easiest way to use OpenTargets MCP is through the hosted service provided by Open Targets infrastructure.

> **Note**: The official hosted endpoint is currently planned and will be announced when deployed. The service will use [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http).

Once available, you can configure Claude Desktop to use the hosted service:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "open-targets-platform-mcp": {
      "type": "url",
      "url": "https://mcp.platform.opentargets.org/mcp"
    }
  }
}
```

## Local Deployment

### Via uvx (Quick Start)

The fastest way to get started is using `uvx`, which will automatically download and run the package directly from GitHub.

The package provides two command variants:
- `otp-mcp` - Shorter alias (recommended)
- `open-targets-platform-mcp` - Full command name

Both commands are functionally identical. Examples:

```bash
# Start stdio server
uvx --from git+https://github.com/opentargets/open-targets-platform-mcp@dev-refactoring otp-mcp --transport stdio

# With jq filtering enabled
uvx --from git+https://github.com/opentargets/open-targets-platform-mcp@dev-refactoring otp-mcp --transport stdio --jq

# Start HTTP server
uvx --from git+https://github.com/opentargets/open-targets-platform-mcp@dev-refactoring otp-mcp --transport http --host 127.0.0.1 --port 8000
```

### Docker Deployment

You can run the MCP server using the official Docker image:

```bash
# Pull the latest image
docker pull ghcr.io/opentargets/platform-mcp:build-pipeline

# Run with stdio transport (for Claude Desktop)
docker run -it --rm \
  -e OTP_MCP_TRANSPORT=stdio \
  -e OTP_MCP_JQ_ENABLED=false \
  ghcr.io/opentargets/platform-mcp:build-pipeline

# Run with HTTP transport
docker run -it --rm \
  -p 8000:8000 \
  -e OTP_MCP_TRANSPORT=http \
  -e OTP_MCP_HTTP_HOST=0.0.0.0 \
  -e OTP_MCP_HTTP_PORT=8000 \
  -e OTP_MCP_JQ_ENABLED=true \
  ghcr.io/opentargets/platform-mcp:build-pipeline
```

For available environment variables, see the [Environment Variables](#environment-variables) table.

## Advanced Deployment

Both advanced deployment options require cloning the repository first:

```bash
# Clone the repository
git clone https://github.com/opentargets/open-targets-platform-mcp.git
cd open-targets-platform-mcp

# Install dependencies
uv sync
```

### FastMCP CLI

For advanced usage and to exploit all FastMCP options, you can use the FastMCP CLI directly with the server module:

```bash
# Install fastmcp (clone the FastMCP repository)
git clone https://github.com/jlowin/fastmcp.git
cd fastmcp
pip install -e .

# Run using FastMCP CLI
cd ../open-targets-platform-mcp
fastmcp run ./src/open_targets_platform_mcp/server.py --transport http
```

> **Note**: For all FastMCP CLI options, see the [FastMCP documentation](https://gofastmcp.com/patterns/cli#fastmcp-run).  
> **Configuration**: Use environment variables (see [Environment Variables](#environment-variables) table) to configure the server when using FastMCP CLI.

### Development Installation (Editable)

For development or to modify the codebase:

```bash
# Install the package in editable mode
uv pip install -e .

# Run the server
otp-mcp --transport stdio
```

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

### Claude Desktop Configuration

To use the MCP server with Claude Desktop, you need to configure it in your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Using Remote Hosted Service

Once the official hosted service is available (see [Remote MCP Server](#remote-mcp-server) section), use this configuration:

```json
{
  "mcpServers": {
    "open-targets-platform-mcp": {
      "type": "url",
      "url": "https://mcp.platform.opentargets.org/mcp"
    }
  }
}
```

#### Using Local Installation

For local deployment, see the [Local Deployment](#local-deployment) section. Here's the Claude Desktop configuration for a local installation:

**Prerequisites:**
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

**Installation:**
```bash
git clone https://github.com/opentargets/open-targets-platform-mcp.git
cd open-targets-platform-mcp
uv sync
```

**Claude Desktop Configuration:**

```json
{
  "mcpServers": {
    "open-targets-platform-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/open-targets-platform-mcp",
        "otp-mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

To enable jq filtering support (see [JQ Filtering](#jq-filtering-optional) section):

```json
{
  "mcpServers": {
    "open-targets-platform-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/open-targets-platform-mcp",
        "otp-mcp",
        "--transport",
        "stdio",
        "--jq"
      ]
    }
  }
}
```

#### Command Line Usage

```bash
# Start HTTP server (for testing/development)
uv run otp-mcp --transport http
uv run otp-mcp --transport http --host 127.0.0.1 --port 8000
uv run otp-mcp --transport http --jq  # with jq filtering

# Start stdio server
uv run otp-mcp --transport stdio
uv run otp-mcp --transport stdio --jq  # with jq filtering

# List available tools
uv run otp-mcp --list-tools
uv run otp-mcp --list-tools --jq  # show tools with jq support
```

#### Environment Variables {#environment-variables}

Configure the server using environment variables (all prefixed with `OTP_MCP_`). The following table shows all available configuration options:

| Environment Variable | CLI Option | Description | Default |
|---------------------|------------|-------------|---------|
| `OTP_MCP_API_ENDPOINT` | `--api` | OpenTargets API endpoint URL | `https://api.platform.opentargets.org/api/v4/graphql` |
| `OTP_MCP_SERVER_NAME` | *(no CLI option)* | Server name displayed in MCP | `"Model Context Protocol server for Open Targets Platform"` |
| `OTP_MCP_TRANSPORT` | `--transport` | Transport type: `stdio` or `http` | `http` |
| `OTP_MCP_HTTP_HOST` | `--host` | HTTP server host (only used with `http` transport) | `localhost` |
| `OTP_MCP_HTTP_PORT` | `--port` | HTTP server port (only used with `http` transport) | `8000` |
| `OTP_MCP_API_CALL_TIMEOUT` | `--timeout` | Request timeout in seconds for API calls | `30` |
| `OTP_MCP_JQ_ENABLED` | `--jq` | Enable jq filtering support | `false` |

**Examples:**

Using environment variables:
```bash
export OTP_MCP_TRANSPORT=stdio
export OTP_MCP_JQ_ENABLED=false
otp-mcp
```

Using CLI options:
```bash
otp-mcp --transport stdio --no-jq
```

**Note:** CLI options take precedence over environment variables when both are provided.

### JQ Filtering (Optional)

The MCP server supports optional server-side JSON filtering using jq expressions. This feature is **disabled by default** but can be enabled if you want to reduce token consumption.

#### When to Use JQ Filtering

JQ filtering is disabled by default. Enable it when:
- You want to reduce token consumption by extracting only specific fields from API responses
- Working with large API responses where only a subset of data is needed
- The calling LLM is proficient at tool calling and can reliably construct jq filters

Disable jq filtering when:
- Simplicity is preferred over optimization
- Working with straightforward queries that don't benefit from filtering
- The LLM should receive complete API responses

#### Enabling JQ Filtering

**Via CLI flag:**
```bash
otp-mcp --transport stdio --jq
otp-mcp --transport http --jq
```

**Via environment variable:**
```bash
export OTP_MCP_JQ_ENABLED=true  # Enable jq (it's disabled by default)
otp-mcp --transport stdio
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
# Install the package with development dependencies
uv sync --dev

# Install pre-commit hooks (if configured)
uv run pre-commit install
```

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
open-targets-platform-mcp/
├── src/open_targets_platform_mcp/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Command-line interface
│   ├── create_server.py     # MCP server creation and setup
│   ├── server.py            # FastMCP server instance
│   ├── settings.py          # Configuration management (pydantic-settings)
│   ├── types.py             # Type definitions (TransportType, etc.)
│   ├── client/              # GraphQL client utilities
│   │   ├── __init__.py
│   │   └── graphql.py       # GraphQL client implementation
│   ├── model/               # Data models
│   │   └── result.py        # Query result models
│   ├── tools/               # MCP tools (organized by feature)
│   │   ├── __init__.py      # Tool exports
│   │   ├── schema/          # Schema fetching tool
│   │   │   ├── schema.py
│   │   │   └── schema.txt
│   │   ├── query/           # Query execution tool
│   │   │   ├── query.py
│   │   │   ├── with_jq_description.txt
│   │   │   └── without_jq_description.txt
│   │   ├── batch_query/     # Batch query tool
│   │   │   ├── batch_query.py
│   │   │   ├── with_jq_description.txt
│   │   │   └── without_jq_description.txt
│   │   └── search_entities/ # Entity search tool
│   │       ├── search_entities.py
│   │       └── description.txt
│   └── static/              # Static assets
│       └── favicon.png
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_client/
│   │   └── test_graphql.py
│   ├── test_tools/
│   │   ├── test_schema.py
│   │   ├── test_query.py
│   │   └── test_batch_query.py
│   ├── test_config.py
│   └── test_server.py
└── pyproject.toml           # Project configuration and dependencies
```


## Contributing

Contributions are welcome! Please open an issue or submit a pull request on the [GitHub repository](https://github.com/opentargets/open-targets-platform-mcp).

## License

This project is licensed under the terms of the license specified in [LICENSE](LICENSE).

## Acknowledgements

We would like to thank the developers from [@biocontext-ai](https://github.com/biocontext-ai) whose implementation of a GraphQL-based MCP server served as an inspiration for this project.

---

Repository initiated with [fpgmaas/cookiecutter-uv](https://github.com/fpgmaas/cookiecutter-uv).
