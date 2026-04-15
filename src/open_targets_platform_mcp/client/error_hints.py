"""Build structured hints from Open Targets GraphQL error messages.

The upstream API uses Sangria, whose validation messages differ slightly from
graphql-core's. Each pattern in `_PATTERNS` was verified against live API
responses. A matched message is enriched with type/field context and, when a
parsed `GraphQLSchema` is available, the list of valid alternatives plus
difflib-based "did you mean" suggestions.

The builder is best-effort: malformed inputs degrade to a passthrough hint
with `category="unrecognized"` rather than raising.
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from graphql import (
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
)

# Cap on `available_fields` / `available_arguments` lists. The Query root type
# has many fields; without a cap a single hint balloons the response payload.
_MAX_AVAILABLE = 50
_DYM_LIMIT = 3
_DYM_CUTOFF = 0.6


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "unknown_field",
        re.compile(
            r"^Cannot query field '(?P<field>[^']+)' on type '(?P<type>[^']+)'\."
            r"(?:\s*Did you mean '(?P<dym>[^']+)'\?)?",
        ),
    ),
    (
        "unknown_argument",
        re.compile(
            r"^Unknown argument '(?P<arg>[^']+)' on field '(?P<field>[^']+)' of type '(?P<type>[^']+)'\.",
        ),
    ),
    (
        "missing_required_argument",
        re.compile(
            r"^Field '(?P<field>[^']+)' argument '(?P<arg>[^']+)' "
            r"of type '(?P<type>[^']+)' is required but not provided\.",
        ),
    ),
    (
        "missing_subselection",
        re.compile(
            r"^Field '(?P<field>[^']+)' of type '(?P<type>[^']+)' must have a sub selection\.",
        ),
    ),
    (
        "variable_type_mismatch",
        re.compile(
            r"^Variable '\$(?P<var>[^']+)' of type '(?P<got>[^']+)' "
            r"used in position expecting type '(?P<want>[^']+)'\.",
        ),
    ),
    (
        "undeclared_variable",
        re.compile(r"^Variable '\$(?P<var>[^']+)' is not defined\."),
    ),
]


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
    for category, pattern in _PATTERNS:
        match = pattern.match(message)
        if not match:
            continue
        groups = match.groupdict()
        builder = _BUILDERS[category]
        payload = builder(groups, schema)
        # Re-categorise unknown_field on Query as unknown_root_query so callers
        # can branch on the more specific intent.
        actual_category = (
            "unknown_root_query"
            if category == "unknown_field" and groups.get("type") == "Query"
            else category
        )
        return {"error_index": idx, "category": actual_category, **payload}
    return {"error_index": idx, "category": "unrecognized", "raw_message": message}


def _build_unknown_field(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    type_name = groups["type"]
    field = groups["field"]
    server_dym = groups.get("dym")
    out: dict[str, Any] = {"type": type_name, "field": field}

    available = _get_field_names(schema, type_name)
    suggestions: list[str] = []
    if available is not None:
        names, truncated = available
        out["available_fields"] = names
        out["available_fields_truncated"] = truncated
        suggestions = _close_matches_ci(field or "", names)
    if server_dym and server_dym not in suggestions:
        suggestions = [server_dym, *suggestions][:_DYM_LIMIT]
    out["did_you_mean"] = suggestions
    return out


def _build_unknown_argument(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    type_name = groups["type"]
    field = groups["field"]
    arg = groups["arg"]
    out: dict[str, Any] = {"type": type_name, "field": field, "argument": arg}
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
    out: dict[str, Any] = {"field": field, "type": raw_type, "inner_type": inner_type}
    available = _get_field_names(schema, inner_type)
    if available is not None:
        names, truncated = available
        out["available_fields"] = names
        out["available_fields_truncated"] = truncated
    return out


def _build_variable_type_mismatch(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    return {"variable": groups["var"], "got": groups["got"], "want": groups["want"]}


def _build_undeclared_variable(
    groups: dict[str, str | None],
    schema: GraphQLSchema | None,
) -> dict[str, Any]:
    var = groups["var"]
    return {
        "variable": var,
        "hint": (
            f"Declare ${var} in the operation signature, e.g. "
            f"`query OpName(${var}: SomeType!) {{ ... }}`."
        ),
    }


_BUILDERS = {
    "unknown_field": _build_unknown_field,
    "unknown_argument": _build_unknown_argument,
    "missing_required_argument": _build_missing_required_argument,
    "missing_subselection": _build_missing_subselection,
    "variable_type_mismatch": _build_variable_type_mismatch,
    "undeclared_variable": _build_undeclared_variable,
}


def _close_matches_ci(needle: str, haystack: list[str]) -> list[str]:
    """Case-insensitive `difflib.get_close_matches`.

    Agents commonly mistype field/argument names with the wrong case
    (e.g. `symbol` vs `approvedSymbol`). We compare lowercased forms but
    return the originals so the suggestion is copy-pasteable into a query.
    """
    if not needle or not haystack:
        return []
    lowered = [h.lower() for h in haystack]
    matches = difflib.get_close_matches(needle.lower(), lowered, n=_DYM_LIMIT, cutoff=_DYM_CUTOFF)
    # Map each matched lowercased value back to its first original.
    out: list[str] = []
    for m in matches:
        for original, lower in zip(haystack, lowered, strict=True):
            if lower == m and original not in out:
                out.append(original)
                break
    return out


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


def _get_field_names(
    schema: GraphQLSchema | None,
    type_name: str | None,
) -> tuple[list[str], bool] | None:
    if schema is None or not type_name:
        return None
    type_def = schema.type_map.get(type_name)
    if not isinstance(type_def, GraphQLObjectType | GraphQLInterfaceType):
        return None
    names = list(type_def.fields.keys())
    truncated = len(names) > _MAX_AVAILABLE
    return (names[:_MAX_AVAILABLE] if truncated else names), truncated


def _get_argument_names(
    schema: GraphQLSchema | None,
    type_name: str | None,
    field_name: str | None,
) -> list[str] | None:
    if schema is None or not type_name or not field_name:
        return None
    type_def = schema.type_map.get(type_name)
    if not isinstance(type_def, GraphQLObjectType | GraphQLInterfaceType):
        return None
    field = type_def.fields.get(field_name)
    if field is None:
        return None
    return list(field.args.keys())
