"""Tool for executing GraphQL queries against the OpenTargets API."""

import json
from typing import Annotated, Optional, Union

import jq
from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool()
def query_open_targets_graphql(
    query_string: Annotated[str, Field(description="The GraphQL query string")],
    variables: Annotated[
        Optional[Union[dict, str]],
        Field(
            description="The variables for the GraphQL query. Can be a JSON object or a JSON string. "
            'Example: {"variantId": "19_44908822_C_T"} or \'{"variantId": "19_44908822_C_T"}\''
        ),
    ] = None,
    jq_filter: Annotated[
        Optional[str],
        Field(description="Optional jq filter to pre-filter the JSON response server-side (e.g., '.data.target.id')"),
    ] = None,
) -> dict:
    """Execute a GraphQL query against the Open Targets API after fetching the schema.

    Important: Always first fetch examples using the schema using `get_open_targets_query_examples`. If the examples are
    not sufficient, also get the schema using the `get_open_targets_graphql_schema` tool before executing a query.
    Relying on either of these options provides the necessary context for the query and ensures that the query is valid.

    Queries should use the Ensembl gene ID (e.g., "ENSG00000141510").
    If necessary, first use `get_ensembl_id_from_gene_symbol` to convert gene symbols (e.g., "TP53") to Ensembl IDs.

    If a disease ID is needed, use the `get_efo_id_from_disease_name` tool to get the EFO ID (e.g., "EFO_0004705") for a
    disease name (e.g., "Hypothyroidism").

    Make sure to always start the query string with the keyword `query` followed by the query name.
    The query string should be a valid GraphQL query, and the variables should be a dictionary of parameters
    that the query requires.

    Open Targets provides data on:
    - target: annotations, tractability, mouse models, expression, disease/phenotype associations, available drugs.
    - disease: annotations, ontology, drugs, symptoms, target associations.
    - drug: annotations, mechanisms, indications, pharmacovigilance.
    - variant: annotations, frequencies, effects, consequences, credible sets.
    - studies: annotations, traits, publications, cohorts, credible sets.
    - credibleSet: annotations, variant sets, gene assignments, colocalization.
    - search: index of all platform entities.

    Args:
        query_string (str): The GraphQL query string.
        variables (dict or str, optional): The variables for the GraphQL query. Can be either a dictionary
            or a JSON string that will be parsed. If passing as a string, use valid JSON format.
        jq_filter (str, optional): A jq filter expression to pre-filter the JSON response.
            This allows you to extract specific fields or transform the response data server-side.
            Examples: '.data.target.id', '.data | {id, symbol}', '.data.target | {id: .id, name: .approvedName}'

    Returns:
        dict: The response data from the GraphQL API, optionally filtered by the jq expression.
    """
    try:
        # Parse variables if provided as a JSON string
        parsed_variables: Optional[dict] = variables if isinstance(variables, dict) else None
        if isinstance(variables, str):
            try:
                parsed_variables = json.loads(variables)
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse variables JSON string: {e!s}"}

        response = execute_graphql_query(config.api_endpoint, query_string, parsed_variables)

        # Apply jq filter if provided
        if jq_filter:
            try:
                compiled_filter = jq.compile(jq_filter)
                filtered_results = compiled_filter.input_value(response).all()

                # Handle different result types
                if len(filtered_results) == 1:
                    # Single result: return as-is if dict, wrap if not
                    single_result = filtered_results[0]
                    if isinstance(single_result, dict):
                        return single_result
                    else:
                        return {"result": single_result}
                else:
                    # Multiple results: return as array
                    return {"results": filtered_results}
            except Exception as jq_error:
                return {
                    "error": f"Failed to apply jq filter '{jq_filter}': {jq_error!s}",
                    "original_response": response,
                }
        else:
            return response
    except Exception as e:
        return {"error": f"Failed to execute GraphQL query: {e!s}"}
