## Remote MCP

For most users, connecting through the remote MCP server is the simplest option. Follow the official [Anthropic docs](https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp) using this address: `https://mcp.platform.opentargets.org/mcp`


## Local Installation

For development, testing, or running your own instance, you can install and run the MCP server locally.

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation
```bash
git clone https://github.com/opentargets/open-targets-platform-mcp.git
cd open-targets-platform-mcp
uv sync
```

### Claude Desktop Configuration

Add this to your Claude Desktop configuration file:
```json
{
  "mcpServers": {
    "otp-mcp": {
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

To enable jq filtering support (see [JQ Filtering](#jq-filtering-optional) section), add the `--jq` flag:
```json
{
  "mcpServers": {
    "otp-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/open-targets-platform-mcp",
        "otp-mcp",
        "--transport",
        "stdio"
        "--jq"
      ]
    }
  }
}
```

Alternatively, you can use the `uvx` command as shown in the main [README.md](https://github.com/opentargets/open-targets-platform-mcp#readme).