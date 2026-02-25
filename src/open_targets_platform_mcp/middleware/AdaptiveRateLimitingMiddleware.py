import logging
import sys
from collections import OrderedDict
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitError, TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class AdaptiveRateLimitingMiddleware(Middleware):
    """Adaptive rate limiting middleware.

    This middleware applies rate limiting with different rates for
    gloabal and session requests. With client identification not yet
    implemented, rate is limited by session which leaves the global requests
    such as initialisation open to abuse. This middleware defends against this
    by applying a different rate limit for global and session requests.
    """

    def __init__(
        self,
        global_max_requests_per_second: float,
        global_burst_capacity: int,
        session_max_requests_per_second: float,
        session_burst_capacity: int,
        max_sessions: int = 1000,
    ):
        self.global_max_requests_per_second = global_max_requests_per_second
        self.global_burst_capacity = global_burst_capacity
        self.session_max_requests_per_second = session_max_requests_per_second
        self.session_burst_capacity = session_burst_capacity
        self.max_sessions = max_sessions

        self.global_limiter = TokenBucketRateLimiter(
            self.global_burst_capacity,
            self.global_max_requests_per_second,
        )
        self.session_limiters: OrderedDict[str, TokenBucketRateLimiter] = OrderedDict()

    def _get_session_limiter(self, session_id: str) -> TokenBucketRateLimiter:
        """Get or create a session limiter with LRU eviction."""
        if session_id in self.session_limiters:
            self.session_limiters.move_to_end(session_id)
        else:
            self.session_limiters[session_id] = TokenBucketRateLimiter(
                self.session_burst_capacity,
                self.session_max_requests_per_second,
            )

            if len(self.session_limiters) > self.max_sessions:
                self.session_limiters.popitem(last=False)
                logger.debug(
                    "Session limiter LRU eviction: %d sessions, %d KB",
                    len(self.session_limiters),
                    sys.getsizeof(self.session_limiters) // 1024,
                )

        return self.session_limiters[session_id]

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """Apply rate limiting to established session and global requests."""
        if not context.fastmcp_context or not context.fastmcp_context.request_context:
            allowed = await self.global_limiter.consume()
        else:
            limiter = self._get_session_limiter(context.fastmcp_context.session_id)
            allowed = await limiter.consume()

        if not allowed:
            msg = "Rate limit exceeded"
            raise RateLimitError(msg)

        return await call_next(context)
