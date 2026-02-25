"""Tests for AdaptiveRateLimitingMiddleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from open_targets_platform_mcp.middleware.AdaptiveRateLimitingMiddleware import (
    AdaptiveRateLimitingMiddleware,
)


class TestAdaptiveRateLimitingMiddleware:
    """Tests for AdaptiveRateLimitingMiddleware class."""

    def test_lru_eviction_when_max_sessions_exceeded(self):
        """Test that LRU eviction occurs when max_sessions is exceeded."""
        middleware = AdaptiveRateLimitingMiddleware(
            global_max_requests_per_second=1.0,
            global_burst_capacity=5,
            session_max_requests_per_second=2.0,
            session_burst_capacity=10,
            max_sessions=3,
        )

        # Create 3 sessions (at capacity)
        middleware._get_session_limiter("session1")
        middleware._get_session_limiter("session2")
        middleware._get_session_limiter("session3")

        assert len(middleware.session_limiters) == 3
        assert "session1" in middleware.session_limiters

        # Create 4th session - should evict session1 (least recently used)
        middleware._get_session_limiter("session4")

        assert len(middleware.session_limiters) == 3
        assert "session1" not in middleware.session_limiters
        assert "session2" in middleware.session_limiters
        assert "session3" in middleware.session_limiters
        assert "session4" in middleware.session_limiters

    def test_lru_move_to_end_on_access(self):
        """Test that accessing a session moves it to end (most recently used)."""
        middleware = AdaptiveRateLimitingMiddleware(
            global_max_requests_per_second=1.0,
            global_burst_capacity=5,
            session_max_requests_per_second=2.0,
            session_burst_capacity=10,
            max_sessions=3,
        )

        # Create 3 sessions
        middleware._get_session_limiter("session1")
        middleware._get_session_limiter("session2")
        middleware._get_session_limiter("session3")

        # Access session1 to move it to end
        middleware._get_session_limiter("session1")

        # Create 4th session - should evict session2 (now least recently used)
        middleware._get_session_limiter("session4")

        assert "session1" in middleware.session_limiters
        assert "session2" not in middleware.session_limiters
        assert "session3" in middleware.session_limiters
        assert "session4" in middleware.session_limiters

    @pytest.mark.asyncio
    async def test_on_request_global_limiter(self):
        """Test that global limiter is used for requests without session context."""
        middleware = AdaptiveRateLimitingMiddleware(
            global_max_requests_per_second=10.0,
            global_burst_capacity=10,
            session_max_requests_per_second=2.0,
            session_burst_capacity=5,
        )

        # Mock context without fastmcp_context
        context = MagicMock()
        context.fastmcp_context = None

        # Mock call_next
        call_next = AsyncMock(return_value="response")

        # Mock the consume method to return True
        middleware.global_limiter.consume = AsyncMock(return_value=True)

        result = await middleware.on_request(context, call_next)

        assert result == "response"
        middleware.global_limiter.consume.assert_called_once()
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_request_session_limiter(self):
        """Test that session limiter is used for requests with session context."""
        middleware = AdaptiveRateLimitingMiddleware(
            global_max_requests_per_second=10.0,
            global_burst_capacity=10,
            session_max_requests_per_second=2.0,
            session_burst_capacity=5,
        )

        # Mock context with fastmcp_context
        context = MagicMock()
        context.fastmcp_context.session_id = "test-session"
        context.fastmcp_context.request_context = MagicMock()

        # Mock call_next
        call_next = AsyncMock(return_value="response")

        # Pre-create a session limiter and mock its consume method
        limiter = middleware._get_session_limiter("test-session")
        limiter.consume = AsyncMock(return_value=True)

        result = await middleware.on_request(context, call_next)

        assert result == "response"
        call_next.assert_called_once()
        limiter.consume.assert_called_once()
