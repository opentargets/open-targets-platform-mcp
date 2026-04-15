"""Tests for the GraphQL error-hint builder.

Most patterns are exercised against the mock_graphql_schema fixture
(see conftest.py); patterns whose hint payload depends only on the regex
(e.g. variable_type_mismatch) use schema=None.

The exact message strings used here were captured from live calls against
the upstream Open Targets endpoint during planning, so the regexes are
verified against production behaviour.
"""

from __future__ import annotations

import pytest
from graphql import build_schema

from open_targets_platform_mcp.client.error_hints import build_hints

# ============================================================================
# Captured live messages (verified against api.platform.opentargets.org)
# ============================================================================

LIVE_UNKNOWN_FIELD_TARGET = (
    "Cannot query field 'symbol' on type 'Target'. (line 1, column 48):\n"
    'query { target(ensemblId: "ENSG00000141510") { symbol } }\n'
    "                                               ^"
)
LIVE_UNKNOWN_ROOT_WITH_SERVER_DYM = (
    "Cannot query field 'variantInfo' on type 'Query'. Did you mean 'variant'? "
    "(line 1, column 9):\n"
    'query { variantInfo(variantId: "1_123_A_G") { id } }\n'
    "        ^"
)
LIVE_UNKNOWN_ARGUMENT = (
    "Unknown argument 'id' on field 'target' of type 'Query'. (line 1, column 16):\n"
    'query { target(id: "ENSG00000141510") { id } }\n'
    "               ^"
)
LIVE_MISSING_REQUIRED_ARGUMENT = (
    "Field 'target' argument 'ensemblId' of type 'String!' is required but not provided. "
    "(line 1, column 9):\n"
    "query { target { id } }\n"
    "        ^"
)
LIVE_MISSING_SUBSELECTION = (
    "Field 'proteinIds' of type '[IdAndSource!]!' must have a sub selection. (line 1, column 48):\n"
    'query { target(ensemblId: "ENSG00000141510") { proteinIds } }\n'
    "                                               ^"
)
LIVE_VARIABLE_TYPE_MISMATCH = (
    "Variable '$id' of type 'Int!' used in position expecting type 'String!'. "
    "(line 1, column 9):\n"
    "query Q($id: Int!) { target(ensemblId: $id) { id } }\n"
    "        ^\n"
    " (line 1, column 40):\n"
    "query Q($id: Int!) { target(ensemblId: $id) { id } }\n"
    "                                       ^"
)
LIVE_UNDECLARED_VARIABLE = (
    "Variable '$ensemblId' is not defined. (line 1, column 27):\n"
    "query { target(ensemblId: $ensemblId) { id } }\n"
    "                          ^\n"
    " (line 1, column 1):\n"
    "query { target(ensemblId: $ensemblId) { id } }\n"
    "^"
)


def _err(message: str) -> dict[str, object]:
    return {"message": message, "locations": [{"line": 1, "column": 1}]}


# ============================================================================
# Pattern 1: unknown field
# ============================================================================


class TestUnknownField:
    def test_close_match_suggests_approved_symbol(self, mock_graphql_schema):
        hints = build_hints([_err(LIVE_UNKNOWN_FIELD_TARGET)], mock_graphql_schema)

        assert len(hints) == 1
        h = hints[0]
        assert h["error_index"] == 0
        assert h["category"] == "unknown_field"
        assert h["type"] == "Target"
        assert h["field"] == "symbol"
        assert h["available_fields"] == ["id", "approvedSymbol", "approvedName"]
        assert h["available_fields_truncated"] is False
        assert "approvedSymbol" in h["did_you_mean"]

    def test_no_close_match_returns_empty_dym(self, mock_graphql_schema):
        msg = "Cannot query field 'totallygibberish' on type 'Target'."
        h = build_hints([_err(msg)], mock_graphql_schema)[0]

        assert h["category"] == "unknown_field"
        assert h["did_you_mean"] == []
        assert h["available_fields"] == ["id", "approvedSymbol", "approvedName"]

    def test_no_schema_omits_available_fields(self):
        h = build_hints([_err(LIVE_UNKNOWN_FIELD_TARGET)], schema=None)[0]

        assert h["category"] == "unknown_field"
        assert h["type"] == "Target"
        assert h["field"] == "symbol"
        assert "available_fields" not in h
        assert h["did_you_mean"] == []

    def test_unknown_type_omits_available_fields(self, mock_graphql_schema):
        msg = "Cannot query field 'foo' on type 'NoSuchType'."
        h = build_hints([_err(msg)], mock_graphql_schema)[0]

        assert h["category"] == "unknown_field"
        assert "available_fields" not in h
        assert h["did_you_mean"] == []


# ============================================================================
# Pattern 2: unknown root query (Query type) -- recategorisation
# ============================================================================


class TestUnknownRootQuery:
    def test_recategorised_when_type_is_query(self, mock_graphql_schema):
        h = build_hints([_err(LIVE_UNKNOWN_ROOT_WITH_SERVER_DYM)], mock_graphql_schema)[0]

        assert h["category"] == "unknown_root_query"
        assert h["type"] == "Query"
        assert h["field"] == "variantInfo"

    def test_server_provided_dym_is_extracted(self, mock_graphql_schema):
        h = build_hints([_err(LIVE_UNKNOWN_ROOT_WITH_SERVER_DYM)], mock_graphql_schema)[0]

        # The mock schema's Query has no 'variant', but the server message
        # included "Did you mean 'variant'?" which we extract verbatim.
        assert "variant" in h["did_you_mean"]

    def test_server_dym_kept_with_no_schema(self):
        h = build_hints([_err(LIVE_UNKNOWN_ROOT_WITH_SERVER_DYM)], schema=None)[0]

        assert h["category"] == "unknown_root_query"
        assert h["did_you_mean"] == ["variant"]


# ============================================================================
# Pattern 3: unknown argument
# ============================================================================


class TestUnknownArgument:
    def test_lookup_against_query_target(self, mock_graphql_schema):
        h = build_hints([_err(LIVE_UNKNOWN_ARGUMENT)], mock_graphql_schema)[0]

        assert h["category"] == "unknown_argument"
        assert h["type"] == "Query"
        assert h["field"] == "target"
        assert h["argument"] == "id"
        assert h["available_arguments"] == ["ensemblId"]
        assert isinstance(h["did_you_mean"], list)

    def test_no_schema_omits_available_arguments(self):
        h = build_hints([_err(LIVE_UNKNOWN_ARGUMENT)], schema=None)[0]

        assert h["category"] == "unknown_argument"
        assert h["argument"] == "id"
        assert "available_arguments" not in h
        assert h["did_you_mean"] == []


# ============================================================================
# Pattern 4: missing required argument
# ============================================================================


class TestMissingRequiredArgument:
    def test_captures_field_argument_type(self, mock_graphql_schema):
        h = build_hints([_err(LIVE_MISSING_REQUIRED_ARGUMENT)], mock_graphql_schema)[0]

        assert h["category"] == "missing_required_argument"
        assert h["field"] == "target"
        assert h["argument"] == "ensemblId"
        assert h["type"] == "String!"


# ============================================================================
# Pattern 5: missing subselection
# ============================================================================


class TestMissingSubselection:
    def test_strips_list_and_nonnull_wrappers(self, mock_graphql_schema):
        h = build_hints([_err(LIVE_MISSING_SUBSELECTION)], mock_graphql_schema)[0]

        assert h["category"] == "missing_subselection"
        assert h["field"] == "proteinIds"
        assert h["type"] == "[IdAndSource!]!"
        assert h["inner_type"] == "IdAndSource"
        # Mock schema does not contain IdAndSource, so available_fields is omitted.
        assert "available_fields" not in h

    def test_resolves_known_inner_type(self, mock_graphql_schema):
        msg = "Field 'foo' of type 'Target!' must have a sub selection."
        h = build_hints([_err(msg)], mock_graphql_schema)[0]

        assert h["category"] == "missing_subselection"
        assert h["inner_type"] == "Target"
        assert h["available_fields"] == ["id", "approvedSymbol", "approvedName"]

    def test_strips_nested_wrappers(self):
        msg = "Field 'foo' of type '[[Target!]!]!' must have a sub selection."
        h = build_hints([_err(msg)], schema=None)[0]

        assert h["inner_type"] == "Target"


# ============================================================================
# Pattern 6: variable type mismatch
# ============================================================================


class TestVariableTypeMismatch:
    def test_captures_got_and_want(self):
        h = build_hints([_err(LIVE_VARIABLE_TYPE_MISMATCH)], schema=None)[0]

        assert h["category"] == "variable_type_mismatch"
        assert h["variable"] == "id"
        assert h["got"] == "Int!"
        assert h["want"] == "String!"


# ============================================================================
# Pattern 7: undeclared variable
# ============================================================================


class TestUndeclaredVariable:
    def test_captures_variable_and_hint_text(self):
        h = build_hints([_err(LIVE_UNDECLARED_VARIABLE)], schema=None)[0]

        assert h["category"] == "undeclared_variable"
        assert h["variable"] == "ensemblId"
        assert "$ensemblId" in h["hint"]
        assert "query OpName" in h["hint"]


# ============================================================================
# Cross-cutting behaviour
# ============================================================================


class TestUnrecognized:
    def test_unmatched_message_passes_through(self):
        msg = "Some completely unexpected error format."
        h = build_hints([_err(msg)], schema=None)[0]

        assert h["category"] == "unrecognized"
        assert h["raw_message"] == msg


class TestMultipleErrors:
    def test_one_hint_per_error_with_correct_indices(self, mock_graphql_schema):
        # The unknown-arg case from the live API actually returns BOTH
        # Pattern 3 and Pattern 4 in the same response.
        errors = [
            _err(LIVE_UNKNOWN_ARGUMENT),
            _err(LIVE_MISSING_REQUIRED_ARGUMENT),
            _err("Some unrecognised noise."),
        ]
        hints = build_hints(errors, mock_graphql_schema)

        assert [h["error_index"] for h in hints] == [0, 1, 2]
        assert hints[0]["category"] == "unknown_argument"
        assert hints[1]["category"] == "missing_required_argument"
        assert hints[2]["category"] == "unrecognized"


class TestRobustness:
    @pytest.mark.parametrize(
        "bad_error",
        [
            {},
            {"message": None},
            {"message": 12345},
            {"locations": []},  # missing "message"
        ],
    )
    def test_malformed_error_does_not_raise(self, bad_error, mock_graphql_schema):
        hints = build_hints([bad_error], mock_graphql_schema)

        assert len(hints) == 1
        assert hints[0]["category"] in {"unrecognized"}

    def test_empty_errors_list_returns_empty_hints(self, mock_graphql_schema):
        assert build_hints([], mock_graphql_schema) == []


class TestTruncation:
    def test_available_fields_capped_at_50(self):
        # Build a synthetic schema with a type holding 60 fields.
        field_lines = "\n".join(f"  field{i}: String" for i in range(60))
        sdl = f"type Query {{ q: BigType }} type BigType {{\n{field_lines}\n}}"
        schema = build_schema(sdl)

        msg = "Cannot query field 'nope' on type 'BigType'."
        h = build_hints([_err(msg)], schema)[0]

        assert h["category"] == "unknown_field"
        assert len(h["available_fields"]) == 50
        assert h["available_fields_truncated"] is True
