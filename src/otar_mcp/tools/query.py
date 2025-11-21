"""Tool for executing GraphQL queries against the OpenTargets API."""

import json
from typing import Annotated, Optional, Union

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool(name="query_open_targets_graphql")
def query_open_targets_graphql(
    query_string: Annotated[str, Field(description="GraphQL query string starting with 'query' keyword")],
    variables: Annotated[
        Optional[Union[dict, str]],
        Field(description="Optional variables for the GraphQL query"),
    ] = None,
    jq_filter: Annotated[
        Optional[str],
        Field(description="Optional jq filter to pre-filter the JSON response server-side"),
    ] = None,
) -> dict:
    """Execute GraphQL queries against the Open Targets API.

    WORKFLOW - Follow these steps in order:

    Step 1: RESOLVE IDENTIFIERS
        If user provides common names (gene symbols, disease names, drug names),
        use `search_entity` tool FIRST to convert them to standardized IDs:

        - Targets/Genes: "BRCA2" → ENSEMBL ID "ENSG00000139618"
        - Diseases: "breast cancer" → EFO/MONDO ID "MONDO_0007254"
        - Drugs: "aspirin" → ChEMBL ID "CHEMBL1201583"
        - Variants: Use "chr_pos_ref_alt" format or rsIDs

        Example: search_entity(query_string="BRCA2", entity_names=["target"])

    Step 2: LEARN QUERY STRUCTURE
        Call `get_open_targets_query_examples` with relevant categories
        (e.g., ["target", "disease", "drug"]) to see proper syntax, fields,
        and structure. Use examples as templates.

        If examples lack needed field details OR if you encounter query errors,
        call `get_open_targets_graphql_schema` for complete type definitions.
        NOTE: The schema tool is expensive in terms of tokens - only use it when
        examples don't provide the right information or after encountering errors.

    Step 3: CONSTRUCT QUERY WITH JQ FILTER
        Build GraphQL query using:
        - Standardized IDs from Step 1 (REQUIRED)
        - Query patterns from Step 2
        - jq filter for targeted information extraction

        JQ FILTER REQUIREMENT:
        When you're after specific information, ALWAYS include a jq_filter to return
        ONLY the requested fields. This achieves parsimony by reducing token consumption
        and response size. Never return the full API response when only specific fields
        are needed.

        The jq filter is applied server-side before the response is returned to you,
        extracting only the relevant data and discarding unnecessary fields.

    Step 4: EXECUTE
        Call this tool with query_string, variables, and jq_filter.

    REQUIRED IDENTIFIER FORMATS:
    - Targets/Genes: ENSEMBL IDs (e.g., "ENSG00000139618")
    - Diseases: EFO IDs (e.g., "EFO_0000305") or MONDO IDs (e.g., "MONDO_0007254")
    - Drugs: ChEMBL IDs (e.g., "CHEMBL1201583")
    - Variants: "chr_pos_ref_alt" format (e.g., "19_44908822_C_T") or rsIDs (e.g., "rs7412")
    - Studies: Study IDs (e.g., "GCST90002357")
    - Credible Sets: Study Locus IDs (e.g., "7d68cc9c70351c9dbd2a2c0c145e555d")

    Args:
        query_string: GraphQL query starting with 'query' keyword
        variables: Optional dict or JSON string with query variables
        jq_filter: Optional jq expression to filter the response server-side

    Returns:
        dict: GraphQL response with data field containing targets, diseases, drugs, variants,
              studies or error message.
    """
    try:
        # Parse variables if provided as a JSON string
        parsed_variables: Optional[dict] = variables if isinstance(variables, dict) else None
        if isinstance(variables, str):
            try:
                parsed_variables = json.loads(variables)
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse variables JSON string: {e!s}"}

        return execute_graphql_query(config.api_endpoint, query_string, parsed_variables, jq_filter=jq_filter)
    except Exception as e:
        return {"error": f"Failed to execute GraphQL query: {e!s}"}
