"""Tests for configuration module."""

import pytest

from otar_mcp.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_config_default_values(self, clean_env):
        """Test that Config uses default values when no env vars are set."""
        config = Config()

        assert config.api_endpoint == "https://api.platform.opentargets.org/api/v4/graphql"
        assert config.server_name == "Open Targets MCP"
        assert config.http_host == "127.0.0.1"
        assert config.http_port == 8000
        assert config.timeout == 30

    def test_config_custom_env_values(self, custom_env):
        """Test that Config reads from environment variables."""
        config = Config()

        assert config.api_endpoint == "https://custom.api.test/graphql"
        assert config.server_name == "Test Server"
        assert config.http_host == "0.0.0.0"
        assert config.http_port == 9000
        assert config.timeout == 60

    def test_config_partial_env_values(self, clean_env, monkeypatch):
        """Test that Config uses defaults for missing env vars."""
        monkeypatch.setenv("MCP_SERVER_NAME", "Partial Config")
        monkeypatch.setenv("MCP_HTTP_PORT", "3000")

        config = Config()

        # Custom values
        assert config.server_name == "Partial Config"
        assert config.http_port == 3000

        # Default values for others
        assert config.api_endpoint == "https://api.platform.opentargets.org/api/v4/graphql"
        assert config.http_host == "127.0.0.1"
        assert config.timeout == 30

    def test_config_mcp_url_property(self, clean_env):
        """Test mcp_url property constructs correct URL."""
        config = Config()

        expected_url = "http://127.0.0.1:8000/mcp"
        assert config.mcp_url == expected_url

    def test_config_mcp_url_property_custom_values(self, custom_env):
        """Test mcp_url property with custom host and port."""
        config = Config()

        expected_url = "http://0.0.0.0:9000/mcp"
        assert config.mcp_url == expected_url

    def test_config_port_type_conversion(self, clean_env, monkeypatch):
        """Test that port is converted to int from string env var."""
        monkeypatch.setenv("MCP_HTTP_PORT", "5555")
        config = Config()

        assert isinstance(config.http_port, int)
        assert config.http_port == 5555

    def test_config_timeout_type_conversion(self, clean_env, monkeypatch):
        """Test that timeout is converted to int from string env var."""
        monkeypatch.setenv("OPENTARGETS_TIMEOUT", "120")
        config = Config()

        assert isinstance(config.timeout, int)
        assert config.timeout == 120

    def test_config_invalid_port_raises_error(self, clean_env, monkeypatch):
        """Test that invalid port value raises ValueError."""
        monkeypatch.setenv("MCP_HTTP_PORT", "not_a_number")

        with pytest.raises(ValueError):
            Config()

    def test_config_invalid_timeout_raises_error(self, clean_env, monkeypatch):
        """Test that invalid timeout value raises ValueError."""
        monkeypatch.setenv("OPENTARGETS_TIMEOUT", "invalid")

        with pytest.raises(ValueError):
            Config()

    def test_config_environment_variable_names(self, clean_env, monkeypatch):
        """Test all environment variable names are correctly read."""
        env_vars = {
            "OPENTARGETS_API_ENDPOINT": "https://test1.api/graphql",
            "MCP_SERVER_NAME": "TestName",
            "MCP_HTTP_HOST": "10.0.0.1",
            "MCP_HTTP_PORT": "7777",
            "OPENTARGETS_TIMEOUT": "90",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = Config()

        assert config.api_endpoint == "https://test1.api/graphql"
        assert config.server_name == "TestName"
        assert config.http_host == "10.0.0.1"
        assert config.http_port == 7777
        assert config.timeout == 90

    def test_config_instances_independent(self, clean_env, monkeypatch):
        """Test that Config instances read env vars at initialization time."""
        # Create first config with default values
        config1 = Config()
        assert config1.server_name == "Open Targets MCP"

        # Set env var and create second config
        monkeypatch.setenv("MCP_SERVER_NAME", "Modified Server")
        config2 = Config()

        # First config should still have old value
        assert config1.server_name == "Open Targets MCP"
        # Second config should have new value
        assert config2.server_name == "Modified Server"
