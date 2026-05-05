class JqCompilationError(Exception):
    """Raised when a jq filter cannot be compiled."""

    def __init__(self, inner_exception: Exception | None = None) -> None:
        super().__init__(str(inner_exception))
        self.inner_exception = inner_exception

    inner_exception: Exception | None
