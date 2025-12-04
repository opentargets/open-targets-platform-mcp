"""Configuration management for OpenTargets MCP server."""

import os


class Config:
    """Configuration for OpenTargets MCP server."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables or defaults."""
        self.api_endpoint: str = os.getenv(
            "OPENTARGETS_API_ENDPOINT", "https://api.platform.opentargets.org/api/v4/graphql"
        )
        self.server_name: str = os.getenv("MCP_SERVER_NAME", "Open Targets MCP")
        self.http_host: str = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
        self.http_port: int = int(os.getenv("MCP_HTTP_PORT", "8000"))
        self.timeout: int = int(os.getenv("OPENTARGETS_TIMEOUT", "30"))
        self.jq_enabled: bool = os.getenv("OPENTARGETS_JQ_ENABLED", "false").lower() == "true"

    @property
    def mcp_url(self) -> str:
        """Get the full MCP server URL for HTTP transport."""
        return f"http://{self.http_host}:{self.http_port}/mcp"


# Global configuration instance
config = Config()
