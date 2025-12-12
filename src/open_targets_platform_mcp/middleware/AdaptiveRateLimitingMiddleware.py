from collections import defaultdict
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitError, TokenBucketRateLimiter


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
    ):
        self.global_max_requests_per_second = global_max_requests_per_second
        self.global_burst_capacity = global_burst_capacity
        self.session_max_requests_per_second = session_max_requests_per_second
        self.session_burst_capacity = session_burst_capacity

        self.global_limiter = TokenBucketRateLimiter(
            self.global_burst_capacity,
            self.global_max_requests_per_second,
        )
        self.session_limiters: dict[str, TokenBucketRateLimiter] = defaultdict(
            lambda: TokenBucketRateLimiter(
                self.session_burst_capacity,
                self.session_max_requests_per_second,
            ),
        )

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """Apply rate limiting to established session and global requests."""
        if not context.fastmcp_context or not context.fastmcp_context.request_context:
            allowed = await self.global_limiter.consume()
        else:
            allowed = await self.session_limiters[context.fastmcp_context.session_id].consume()

        if not allowed:
            msg = "Rate limit exceeded"
            raise RateLimitError(msg)

        return await call_next(context)
