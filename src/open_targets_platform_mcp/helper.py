import functools
import inspect
from collections.abc import Callable
from typing import Annotated, Any, cast, get_args, get_origin, get_type_hints

from pydantic.fields import FieldInfo


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


def _render_type(tp: Any) -> str:
    """Render a type hint as a readable string, preserving generic arguments."""
    if tp is type(None):
        return "None"
    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        origin_name = getattr(origin, "__name__", str(origin).replace("typing.", ""))
        if args:
            args_str = ", ".join(_render_type(a) for a in args)
            return f"{origin_name}[{args_str}]"
        return origin_name
    if isinstance(tp, type):
        return tp.__name__
    # Handles things like Union types expressed as X | Y in older runtimes
    return str(tp).replace("typing.", "")


def _build_line(arg_name: str | None, ann: type) -> str:
    if get_origin(ann) is not Annotated:
        msg = "Must be Annotated[..., Field(...)]"
        raise TypeError(msg)

    args = get_args(ann)
    base_type = args[0]
    field = None
    fallback_description = None
    for meta in args[1:]:
        if isinstance(meta, FieldInfo):
            field = meta
            break
        if isinstance(meta, str) and fallback_description is None:
            fallback_description = meta
            break

    if field is None and fallback_description is None:
        msg = "No Field or str metadata found in Annotated"
        raise TypeError(msg)

    line = "    "
    if arg_name is not None:
        line = line + f"{arg_name} "
    line = line + f"({_render_type(base_type)})"
    if field is not None:
        extra = field.description or ""
        examples = field.examples or []
        if examples and len(examples) > 0:
            extra = f"{extra} (examples: {', '.join(map(str, examples))})"
    else:
        extra = fallback_description or ""
    if extra:
        line = f"{line}: {extra}"

    return line


def build_description(func: Callable[..., Any], main_text: str | None) -> str:
    """Build a description of a tool.

    The description is built from the function's signature and type
    annotations, which must use Annotated metadata for all parameters and the
    return type. Field(...) is preferred, with a string metadata fallback.
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)

    main_text = main_text or sig.__doc__
    lines = [main_text.strip()] if main_text else []
    lines.append("")

    # Args
    lines.append("Args:")
    for name in sig.parameters:
        if name in {"self", "cls"}:
            continue

        line = _build_line(name, hints[name])
        lines.append(line)

    # Return
    ret_ann = cast("type", hints.get("return"))
    line = _build_line(None, ret_ann)

    lines.append("")
    lines.append("Returns:")
    lines.append(line)

    return "\n".join(lines)
