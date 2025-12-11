from enum import Enum


class TransportType(str, Enum):
    """Transport type for the server."""

    STDIO = "stdio"
    HTTP = "http"
