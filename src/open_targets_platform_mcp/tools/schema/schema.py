"""Tool for fetching the Open Targets Platform GraphQL schema."""

from typing import Annotated

from graphql import print_schema
from pydantic import Field

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.tools.schema.subschema import (
    _types_to_sdl,
    get_categories_for_docstring,
    get_category_subschemas,
)
from open_targets_platform_mcp.tools.schema.type_graph import get_cached_schema

# Module-level cache for schema (pre-fetched at startup)
_cached_schema: str | None = None


async def prefetch_schema() -> None:
    """Pre-fetch and cache the GraphQL schema at server startup.

    This function should be called once during server initialization
    to ensure the schema is available immediately when requested.
    """
    global _cached_schema  # noqa: PLW0603
    schema_obj = await fetch_graphql_schema()
    _cached_schema = print_schema(schema_obj)


_COMMON_MISTAKES_GUIDE = """
# GRAPHQL VARIABLE DECLARATION REQUIREMENT

When using variables in your query, you MUST declare them in the operation definition.
Queries with undeclared variables will fail.

✅ CORRECT format (variables declared):
    query($ensemblId: String!) {
        target(ensemblId: $ensemblId) {
            approvedSymbol
            approvedName
        }
    }
    variables: {"ensemblId": "ENSG00000139618"}

❌ INCORRECT format (variables NOT declared - WILL FAIL):
    query {
        target(ensemblId: $ensemblId) {
            approvedSymbol
        }
    }

Alternatively, you can inline the values directly (no variables needed):
    query {
        target(ensemblId: "ENSG00000139618") {
            approvedSymbol
            approvedName
        }
    }

# COMMON MISTAKES TO AVOID

## 1. Wrong argument names for root queries (use specific ID parameter, NOT generic "id"):
   ❌ target(id: "ENSG...")           →  ✅ target(ensemblId: "ENSG...")
   ❌ disease(id: "EFO_...")          →  ✅ disease(efoId: "EFO_...")
   ❌ variant(id: "1_123_A_G")        →  ✅ variant(variantId: "1_123_A_G")
   ❌ drug(id: "CHEMBL...")           →  ✅ drug(chemblId: "CHEMBL...")

## 2. Wrong field names:
   ❌ target { symbol }               →  ✅ target { approvedSymbol }
   ❌ target { name }                 →  ✅ target { approvedName }
   ❌ drug { chemblId }               →  ✅ drug { id }  (chemblId IS the id)
   ❌ study { studyId }               →  ✅ study { id }  (studyId IS the id)

## 3. Non-existent root queries:
   ❌ variantInfo(...)                →  ✅ variant(variantId: ...)
   ❌ variants(variantIds: [...])     →  Use batch_query with variant() instead

## 4. Fields requiring subselections (cannot query scalar-style):
   ❌ target { proteinIds }           →  ✅ target { proteinIds { id source } }
   ❌ target { synonyms }             →  ✅ target { synonyms { label source } }
   ❌ disease { synonyms }            →  ✅ disease { synonyms { terms } }

# WORKING EXAMPLES

## Example 1 - Target query showing correct argument (ensemblId) and field names (approvedSymbol):
    query {
        target(ensemblId: "ENSG00000141510") {
            approvedSymbol
            approvedName
            biotype
        }
    }

## Example 2 - Drug query showing that "id" field returns the ChEMBL ID (don't use chemblId field):
    query {
        drug(chemblId: "CHEMBL1201583") {
            id
            name
            maximumClinicalTrialPhase
            hasBeenWithdrawn
        }
    }

## Example 3 - Disease query showing correct argument (efoId) and pagination with associatedTargets:
    query {
        disease(efoId: "EFO_0000311") {
            id
            name
            associatedTargets(page: {index: 0, size: 10}) {
                count
                rows {
                    target { approvedSymbol }
                    score
                }
            }
        }
    }

## Example 4 - Variant query showing correct argument (variantId) instead of wrong "id" or "variantInfo":
    query {
        variant(variantId: "19_44908822_C_T") {
            id
            rsIds
            mostSevereConsequence { id label }
        }
    }

## Example 5 - Target query showing fields that require subselections (proteinIds, synonyms):
    query {
        target(ensemblId: "ENSG00000141510") {
            approvedSymbol
            proteinIds { id source }
            synonyms { label source }
        }
    }
"""


async def get_open_targets_graphql_schema(
    categories: Annotated[
        list[str],
        Field(
            description="List of category names to filter the schema. "
            "Returns only types relevant to the specified categories.",
        ),
    ],
) -> str:
    """Retrieve the Open Targets Platform GraphQL schema by category."""
    if _cached_schema is None:
        msg = "Schema not initialized. Call prefetch_schema() at server startup."
        raise RuntimeError(msg)

    # Get subschemas for requested categories
    subschemas = get_category_subschemas()
    available_categories = sorted(subschemas.subschemas.keys())

    # Validate category names
    invalid_categories = [c for c in categories if c not in subschemas.subschemas]
    if invalid_categories:
        msg = (
            f"Invalid category name(s): {', '.join(invalid_categories)}. "
            f"Available categories: {', '.join(available_categories)}"
        )
        raise ValueError(msg)

    # Collect all types from requested categories
    all_types: set[str] = set()
    for category_name in categories:
        all_types.update(subschemas.subschemas[category_name].types)

    # Generate combined SDL
    schema_obj = get_cached_schema()
    sdl = _types_to_sdl(all_types, schema_obj)

    # Append common mistakes guide
    return sdl + "\n" + _COMMON_MISTAKES_GUIDE


# Dynamically set the docstring with the categories list
get_open_targets_graphql_schema.__doc__ = f"""\
Retrieve the Open Targets Platform GraphQL schema filtered by category.

You MUST specify one or more categories to retrieve the relevant schema subset.
Categories group related GraphQL types into coherent subschemas
(e.g., 'drug-mechanisms', 'genetic-associations', 'target-safety').

The returned schema includes types from the specified categories plus
their dependencies expanded..

Args:
    categories: List of category names to filter the schema. At least
        one category must be specified.

Returns:
    str: the schema text in SDL (Schema Definition Language) format.

Raises:
    RuntimeError: If schema was not pre-fetched at startup.
    ValueError: If an invalid category name is provided.

Examples:
    - get_open_targets_graphql_schema(["drug-mechanisms"]) -> drug types
    - get_open_targets_graphql_schema(["target-safety", "drug-safety"])
        -> combined safety-related types

{get_categories_for_docstring()}
"""
