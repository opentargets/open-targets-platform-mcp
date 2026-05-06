"""Rate limiting middleware with workarounds for FastMCP quirks."""

from fastmcp.server.middleware.middleware import CallNext, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

_EXEMPT_METHODS = frozenset({"initialize", "tools/list"})


class HandshakeExemptRateLimitingMiddleware(RateLimitingMiddleware):
    """RateLimitingMiddleware that exempts certain MCP handshake methods.

    Workaround for a FastMCP bug where McpError raised during 'initialize'
    middleware is caught by session.py's validation error handler and
    incorrectly reported as INVALID_PARAMS to the client.

    Exempting 'initialize' and 'tools/list' to always allow agent clients to
    register the MCP server.
    """

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> object:
        if context.method in _EXEMPT_METHODS:
            return await call_next(context)
        return await super().on_request(context, call_next)
