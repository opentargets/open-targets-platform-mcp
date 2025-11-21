"""Tool for executing GraphQL queries against the OpenTargets API."""

from typing import Annotated, Optional

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.server import mcp


@mcp.tool()
def query_open_targets_graphql(
    query_string: Annotated[str, Field(description="The GraphQL query string")],
    variables: Annotated[Optional[dict], Field(description="The variables for the GraphQL query")] = None,
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
        variables (dict): The variables for the GraphQL query.

    Returns:
        dict: The response data from the GraphQL API.
    """
    try:
        response = execute_graphql_query(config.api_endpoint, query_string, variables)
    except Exception as e:
        return {"error": f"Failed to execute GraphQL query: {e!s}"}
    else:
        return response
