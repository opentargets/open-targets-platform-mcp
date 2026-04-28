"""Build structured hints from Open Targets GraphQL error messages.

The upstream API uses Sangria, whose validation messages differ slightly from
graphql-core's. Each pattern in `_RULES` was verified against live API
responses. A matched message is enriched with type/field context and, when a
parsed `GraphQLSchema` is available, the list of valid alternatives plus
"did you mean" suggestions drawn from the server's own hints, case-insensitive
substring matches, and difflib fuzzy matches.

The builder is best-effort: malformed inputs degrade to a passthrough hint
with `category="unrecognized"` rather than raising.
"""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING, Any, cast

from graphql import (
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Cap on `available_fields` / `available_arguments` lists. The Query root type
# has many fields; without a cap a single hint balloons the response payload.
_MAX_AVAILABLE = 50
_DYM_LIMIT = 3
_DYM_CUTOFF = 0.6
# Below this length, needles are too generic for substring matching to help
# (e.g. `id` would pull in every `*Id` field). Agents typing 3+ characters
# are usually dropping a conventional prefix (`approvedName` -> `name`).
_SUBSTRING_MIN = 3

# Extracts every quoted name from a Sangria "Did you mean 'X', 'Y' or 'Z'?"
# fragment. Sangria emits up to 4 alternatives; all are kept because the
# server has full schema context and its picks are the most reliable signal
# for partial-term mistakes.
_QUOTED_NAME = re.compile(r"'([^']+)'")


def build_hints(
    errors: list[dict[str, Any]],
    schema: GraphQLSchema | None,
) -> list[dict[str, Any]]:
    """Build a hint dict per error.

    Args:
        errors: GraphQL `errors` array as returned by the upstream API. Each
            entry is expected to have at least a `message` string.
        schema: Optional parsed `GraphQLSchema` for looking up valid fields and
            arguments. When None, regex-derived hint fields still ship; only
            schema-derived `available_fields`/`available_arguments`/`did_you_mean`
            are omitted.

    Returns:
        One hint dict per input error, in the same order. Each hint always has
        `error_index` and `category` keys. Unmatched messages get
        `category="unrecognized"` with the raw `message` preserved.
    """
    hints: list[dict[str, Any]] = []
    for idx, error in enumerate(errors):
        try:
            hints.append(_build_one(idx, error, schema))
        except Exception:
            hints.append(
                {
                    "error_index": idx,
                    "category": "unrecognized",
                    "raw_message": _safe_message(error),
                },
            )
    return hints


def _safe_message(error: Any) -> str:
    if isinstance(error, dict):
        msg = error.get("message", "")
        return msg if isinstance(msg, str) else str(msg)
    return str(error)


def _build_one(
    idx: int,
    error: dict[str, Any],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    message = _safe_message(error)
    for pattern, builder in _RULES:
        match = pattern.match(message)
        if match:
            return {"error_index": idx, **builder(match.groupdict(), schema)}
    return {"error_index": idx, "category": "unrecognized", "raw_message": message}


def _build_unknown_field(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    type_name = groups["type"]
    field = groups["field"]
    # Split unknown-field on the Query root into its own category so callers
    # can distinguish "missing tool" from "typo inside a subselection".
    category = "unknown_root_query" if type_name == "Query" else "unknown_field"
    out: dict[str, Any] = {"category": category, "type": type_name, "field": field}

    available = _get_field_names(schema, type_name)
    local_suggestions: list[str] = []
    if available is not None:
        names, truncated = available
        out["available_fields"] = names[:_MAX_AVAILABLE]
        out["available_fields_truncated"] = truncated
        # Fuzzy matching runs on the full list so suggestions can reach
        # fields past the cap on wide types like `Evidence` (106 fields).
        local_suggestions = _close_matches_ci(field or "", names)
    # Server-provided alternatives lead: Sangria sees the full schema and
    # ranks candidates, typically returning 1-4 for partial-term mistakes.
    server_suggestions = _QUOTED_NAME.findall(groups.get("dym_fragment") or "")
    out["did_you_mean"] = _dedupe_cap([*server_suggestions, *local_suggestions])
    return out


def _dedupe_cap(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
            if len(out) >= _DYM_LIMIT:
                break
    return out


def _build_unknown_argument(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    type_name = groups["type"]
    field = groups["field"]
    arg = groups["arg"]
    out: dict[str, Any] = {
        "category": "unknown_argument",
        "type": type_name,
        "field": field,
        "argument": arg,
    }
    available = _get_argument_names(schema, type_name, field)
    suggestions: list[str] = []
    if available is not None:
        out["available_arguments"] = available
        suggestions = _close_matches_ci(arg or "", available)
    out["did_you_mean"] = suggestions
    return out


def _build_missing_required_argument(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    return {
        "category": "missing_required_argument",
        "field": groups["field"],
        "argument": groups["arg"],
        "type": groups["type"],
    }


def _build_missing_subselection(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    field = groups["field"]
    raw_type = groups["type"] or ""
    inner_type = _strip_wrappers(raw_type)
    out: dict[str, Any] = {
        "category": "missing_subselection",
        "field": field,
        "type": raw_type,
        "inner_type": inner_type,
    }
    available = _get_field_names(schema, inner_type)
    if available is not None:
        names, truncated = available
        out["available_fields"] = names[:_MAX_AVAILABLE]
        out["available_fields_truncated"] = truncated
    return out


def _build_variable_type_mismatch(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    return {
        "category": "variable_type_mismatch",
        "variable": groups["var"],
        "got": groups["got"],
        "want": groups["want"],
    }


def _build_undeclared_variable(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    var = groups["var"]
    return {
        "category": "undeclared_variable",
        "variable": var,
        "hint": (
            f"Declare ${var} in the operation signature, e.g. "
            f"`query OpName(${var}: SomeType!) {{ ... }}`."
        ),
    }


_RULES = [
    (
        re.compile(
            r"^Cannot query field '(?P<field>[^']+)' on type '(?P<type>[^']+)'\."
            r"(?P<dym_fragment>\s*Did you mean [^?]*\?)?",
        ),
        _build_unknown_field,
    ),
    (
        re.compile(
            r"^Unknown argument '(?P<arg>[^']+)' on field '(?P<field>[^']+)' of type '(?P<type>[^']+)'\.",
        ),
        _build_unknown_argument,
    ),
    (
        re.compile(
            r"^Field '(?P<field>[^']+)' argument '(?P<arg>[^']+)' "
            r"of type '(?P<type>[^']+)' is required but not provided\.",
        ),
        _build_missing_required_argument,
    ),
    (
        re.compile(
            r"^Field '(?P<field>[^']+)' of type '(?P<type>[^']+)' must have a sub selection\.",
        ),
        _build_missing_subselection,
    ),
    (
        re.compile(
            r"^Variable '\$(?P<var>[^']+)' of type '(?P<got>[^']+)' "
            r"used in position expecting type '(?P<want>[^']+)'\.",
        ),
        _build_variable_type_mismatch,
    ),
    (
        re.compile(r"^Variable '\$(?P<var>[^']+)' is not defined\."),
        _build_undeclared_variable,
    ),
]


def _close_matches_ci(needle: str, haystack: list[str]) -> list[str]:
    """Case-insensitive "did you mean" suggestions.

    Two strategies are combined, substring hits first:
    1. Substring match catches dropped-prefix mistakes (e.g. `approvedName`
       typed as `name`), which difflib's ratio penalises too heavily to
       surface — `name` vs `approvedName` scores 0.5, below the 0.6 cutoff.
    2. `difflib.get_close_matches` fills remaining slots for typos and
       transpositions.

    Matches are returned case-preserved so they're copy-pasteable, and
    capped at `_DYM_LIMIT`.
    """
    if not needle or not haystack:
        return []
    needle_lower = needle.lower()
    suggestions: list[str] = []
    if len(needle_lower) >= _SUBSTRING_MIN:
        for candidate in haystack:
            if needle_lower in candidate.lower() and candidate not in suggestions:
                suggestions.append(candidate)
                if len(suggestions) >= _DYM_LIMIT:
                    return suggestions
    lower_to_original: dict[str, str] = {}
    for h in haystack:
        lower_to_original.setdefault(h.lower(), h)
    matches = difflib.get_close_matches(
        needle_lower, list(lower_to_original), n=_DYM_LIMIT, cutoff=_DYM_CUTOFF,
    )
    for m in matches:
        original = lower_to_original[m]
        if original not in suggestions:
            suggestions.append(original)
            if len(suggestions) >= _DYM_LIMIT:
                break
    return suggestions


def _strip_wrappers(type_str: str) -> str:
    """Strip `!` and `[]` wrappers from a GraphQL type string.

    `[Foo!]!` -> `Foo`. Preserves the inner name so it can be looked up in the
    schema's `type_map`.
    """
    s = type_str.strip()
    while True:
        if s.endswith("!"):
            s = s[:-1].rstrip()
            continue
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1].strip()
            continue
        return s


def _resolve_type(
    schema: GraphQLSchema | None,
    type_name: str | None,
) -> GraphQLObjectType | GraphQLInterfaceType | None:
    if schema is None or not type_name:
        return None
    type_def = schema.type_map.get(type_name)
    if isinstance(type_def, GraphQLObjectType | GraphQLInterfaceType):
        return type_def
    return None


def _get_field_names(
    schema: GraphQLSchema | None,
    type_name: str | None,
) -> tuple[list[str], bool] | None:
    """Return the full list of fields plus a truncation flag.

    The list is returned in full so fuzzy matching can reach fields past
    `_MAX_AVAILABLE` on wide types (e.g. `Evidence` has 106 fields).
    Callers should slice `[:_MAX_AVAILABLE]` when shipping
    `available_fields` to the client; the flag indicates whether that
    slice would lose entries.
    """
    type_def = _resolve_type(schema, type_name)
    if type_def is None:
        return None
    names = list(type_def.fields.keys())
    return names, len(names) > _MAX_AVAILABLE


def _get_argument_names(
    schema: GraphQLSchema | None,
    type_name: str | None,
    field_name: str | None,
) -> list[str] | None:
    type_def = _resolve_type(schema, type_name)
    if type_def is None or not field_name:
        return None
    field = type_def.fields.get(field_name)
    return None if field is None else list(field.args.keys())


# How many `available_fields` to show inline when rendering a
# missing-subselection hint as prose. Past this, the agent should call
# `get_open_targets_graphql_schema` for the full list.
_AVAILABLE_FIELDS_PROSE_CAP = 5

# Slug -> human-readable label for the `error_type` codes raised by
# `client.graphql.execute_graphql_query`. Anything not in the map renders as
# its raw slug, which still parses as readable enough.
_ERROR_TYPE_LABELS: dict[str, str] = {
    "graphql_syntax_error": "GraphQL syntax error",
    "graphql_query_error": "GraphQL query error",
    "server_error": "Open Targets server error",
    "protocol_error": "GraphQL protocol error",
    "connection_error": "Connection failed",
    "timeout": "Request timed out",
    "filter_compile_error": "jq filter compile error",
}


def render_hints_as_prose(hints: list[dict[str, Any]]) -> str:
    """Render hint dicts (output of `build_hints`) as a `  - ` bullet list.

    Returns "" when `hints` is empty so callers can decide whether to append
    a "Hints:" section. One bullet per hint; category-specific formatting.
    Best-effort: a malformed hint falls back to a passthrough bullet rather
    than raising, mirroring `build_hints`.
    """
    if not hints:
        return ""
    lines: list[str] = []
    for hint in hints:
        try:
            line = _render_one_hint(hint)
        except Exception:
            line = f"Unrecognised hint: {hint!r}"
        if line:
            lines.append(f"  - {line}")
    return "\n".join(lines)


def render_error_with_hints(
    error_type: str,
    detail: str,
    hints: list[dict[str, Any]] | None = None,
) -> str:
    """Compose a `<label>: <detail>` line, then optionally a Hints section.

    Used by `client.graphql.execute_graphql_query` to format the message
    string passed to `ToolError(...)`. The output reaches LLM agents as the
    text content of the tool response, so it's optimised for readability.
    """
    label = _ERROR_TYPE_LABELS.get(error_type, error_type)
    body = f"{label}: {detail}"
    if hints:
        prose = render_hints_as_prose(hints)
        if prose:
            body = f"{body}\n\nHints:\n{prose}"
    return body


def _render_one_hint(hint: dict[str, Any]) -> str:
    category = hint.get("category", "unrecognized")
    renderer = _PROSE_RENDERERS.get(category, _render_unrecognized)
    return renderer(hint)


def _did_you_mean_suffix(hint: dict[str, Any]) -> str:
    raw = hint.get("did_you_mean")
    if not raw:
        return ""
    # `build_hints` always emits `did_you_mean` as `list[str]`; the cast
    # tells the type checker that. A malformed value would fail in `join`
    # below and be swallowed by the outer try/except in `render_hints_as_prose`.
    dym = cast("list[str]", raw)
    return f" Did you mean: {', '.join(dym)}?"


def _render_unknown_field(hint: dict[str, Any]) -> str:
    field = hint.get("field") or "?"
    type_name = hint.get("type") or "?"
    return f"Field '{field}' does not exist on type '{type_name}'.{_did_you_mean_suffix(hint)}"


def _render_unknown_root_query(hint: dict[str, Any]) -> str:
    field = hint.get("field") or "?"
    return f"'{field}' is not a top-level Query field.{_did_you_mean_suffix(hint)}"


def _render_unknown_argument(hint: dict[str, Any]) -> str:
    arg = hint.get("argument") or "?"
    field = hint.get("field") or "?"
    type_name = hint.get("type") or "?"
    return (
        f"Argument '{arg}' is not valid on field '{field}' (type {type_name})."
        f"{_did_you_mean_suffix(hint)}"
    )


def _render_missing_required_argument(hint: dict[str, Any]) -> str:
    field = hint.get("field") or "?"
    arg = hint.get("argument") or "?"
    type_name = hint.get("type") or "?"
    return f"Field '{field}' requires argument '{arg}' (type {type_name})."


def _render_missing_subselection(hint: dict[str, Any]) -> str:
    field = hint.get("field") or "?"
    type_name = hint.get("type") or "?"
    inner_type = hint.get("inner_type") or "?"
    base = f"Field '{field}' (type {type_name}) requires a sub-selection."
    raw_available = hint.get("available_fields")
    if not raw_available:
        return base
    # `build_hints` always emits `available_fields` as `list[str]`.
    available = cast("list[str]", raw_available)
    sample = ", ".join(available[:_AVAILABLE_FIELDS_PROSE_CAP])
    truncated = (
        len(available) > _AVAILABLE_FIELDS_PROSE_CAP
        or bool(hint.get("available_fields_truncated"))
    )
    if truncated:
        sample = f"{sample}, ..."
    return f"{base} Available fields on {inner_type}: {sample}."


def _render_variable_type_mismatch(hint: dict[str, Any]) -> str:
    var = hint.get("variable") or "?"
    got = hint.get("got") or "?"
    want = hint.get("want") or "?"
    return f"Variable ${var} is of type {got} but used where {want} is expected."


def _render_undeclared_variable(hint: dict[str, Any]) -> str:
    txt = hint.get("hint")
    if isinstance(txt, str) and txt:
        return txt
    var = hint.get("variable") or "?"
    return f"Variable ${var} is used but not declared in the operation signature."


def _render_unrecognized(hint: dict[str, Any]) -> str:
    raw = hint.get("raw_message")
    if isinstance(raw, str) and raw:
        return raw
    return "Unrecognised GraphQL error."


_PROSE_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "unknown_field": _render_unknown_field,
    "unknown_root_query": _render_unknown_root_query,
    "unknown_argument": _render_unknown_argument,
    "missing_required_argument": _render_missing_required_argument,
    "missing_subselection": _render_missing_subselection,
    "variable_type_mismatch": _render_variable_type_mismatch,
    "undeclared_variable": _render_undeclared_variable,
    "unrecognized": _render_unrecognized,
}
