"""Tests for configuration module."""

import pytest

from open_targets_platform_mcp.settings import Settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_default_values(self, clean_env):
        """Test that Settings uses default values when no env vars are set."""
        settings = Settings()

        assert str(settings.api_endpoint) == "https://api.platform.opentargets.org/api/v4/graphql"
        assert settings.server_name == "Model Context Protocol server for Open Targets Platform"
        assert settings.http_host == "localhost"
        assert settings.http_port == 8000
        assert settings.api_call_timeout == 30
        assert settings.jq_enabled is False

    def test_settings_custom_env_values(self, custom_env):
        """Test that Settings reads from environment variables."""
        settings = Settings()

        assert str(settings.api_endpoint) == "https://custom.api.test/graphql"
        assert settings.server_name == "Test Server"
        assert settings.http_host == "0.0.0.0"
        assert settings.http_port == 9000
        assert settings.api_call_timeout == 60

    def test_settings_partial_env_values(self, clean_env, monkeypatch):
        """Test that Settings uses defaults for missing env vars."""
        monkeypatch.setenv("OTP_MCP_SERVER_NAME", "Partial Config")
        monkeypatch.setenv("OTP_MCP_HTTP_PORT", "3000")

        settings = Settings()

        # Custom values
        assert settings.server_name == "Partial Config"
        assert settings.http_port == 3000

        # Default values for others
        assert str(settings.api_endpoint) == "https://api.platform.opentargets.org/api/v4/graphql"
        assert settings.http_host == "localhost"
        assert settings.api_call_timeout == 30

    def test_settings_port_type_conversion(self, clean_env, monkeypatch):
        """Test that port is converted to int from string env var."""
        monkeypatch.setenv("OTP_MCP_HTTP_PORT", "5555")
        settings = Settings()

        assert isinstance(settings.http_port, int)
        assert settings.http_port == 5555

    def test_settings_timeout_type_conversion(self, clean_env, monkeypatch):
        """Test that timeout is converted to int from string env var."""
        monkeypatch.setenv("OTP_MCP_API_CALL_TIMEOUT", "120")
        settings = Settings()

        assert isinstance(settings.api_call_timeout, int)
        assert settings.api_call_timeout == 120

    def test_settings_invalid_port_raises_error(self, clean_env, monkeypatch):
        """Test that invalid port value raises ValueError."""
        monkeypatch.setenv("OTP_MCP_HTTP_PORT", "not_a_number")

        with pytest.raises(ValueError):
            Settings()

    def test_settings_invalid_timeout_raises_error(self, clean_env, monkeypatch):
        """Test that invalid timeout value raises ValueError."""
        monkeypatch.setenv("OTP_MCP_API_CALL_TIMEOUT", "invalid")

        with pytest.raises(ValueError):
            Settings()

    def test_settings_environment_variable_names(self, clean_env, monkeypatch):
        """Test all environment variable names are correctly read."""
        env_vars = {
            "OTP_MCP_API_ENDPOINT": "https://test1.api/graphql",
            "OTP_MCP_SERVER_NAME": "TestName",
            "OTP_MCP_HTTP_HOST": "10.0.0.1",
            "OTP_MCP_HTTP_PORT": "7777",
            "OTP_MCP_API_CALL_TIMEOUT": "90",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = Settings()

        assert str(settings.api_endpoint) == "https://test1.api/graphql"
        assert settings.server_name == "TestName"
        assert settings.http_host == "10.0.0.1"
        assert settings.http_port == 7777
        assert settings.api_call_timeout == 90

    def test_settings_update_method(self, clean_env):
        """Test that Settings.update() method works."""
        settings = Settings()
        original_name = settings.server_name

        settings.update(server_name="Updated Name")

        assert settings.server_name == "Updated Name"
        assert settings.server_name != original_name
