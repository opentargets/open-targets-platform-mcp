import functools
import inspect
from collections.abc import Callable
from typing import Any


def clone_function_with_removed_parameter(func: Callable[..., Any], param_name: str) -> Callable[..., Any]:
    """Clone a function with a specified parameter removed.

    Used for removing the jq option without repeating function signature
    annotations.
    """
    sig = inspect.signature(func)

    parameters = list(sig.parameters.items())
    if param_name not in sig.parameters:
        msg = f"Parameter '{param_name}' not found in function '{func.__name__}' signature."
        raise ValueError(msg)
    new_sig = sig.replace(parameters=[p for name, p in parameters if name != param_name])

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs.pop(param_name, None)
        return func(*args, **kwargs)

    wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
    return wrapper
