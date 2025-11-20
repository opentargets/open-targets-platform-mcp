from typing import Any, Optional

import jq
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from graphql import GraphQLSchema


def fetch_graphql_schema(endpoint_url: str) -> GraphQLSchema:
    """Fetch the GraphQL schema from the given endpoint URL.

    Args:
        endpoint_url (str): The GraphQL endpoint URL.

    Returns:
        GraphQLSchema: The fetched GraphQL schema.
    """
    # Create a transport with your GraphQL endpoint
    transport = RequestsHTTPTransport(
        url=endpoint_url,
    )

    # Create a client
    client = Client(transport=transport, fetch_schema_from_transport=True)

    with client as _session:
        # The schema is automatically fetched and stored in the client
        if not client.schema:
            msg = "Failed to fetch schema from the GraphQL endpoint."
            raise ValueError(msg)

        return client.schema


def execute_graphql_query(
    endpoint_url: str,
    query_string: str,
    variables: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    jq_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Make a generic GraphQL API call.

    Args:
        endpoint_url (str): The GraphQL endpoint URL
        query_string (str): The GraphQL query or mutation as a string
        variables (dict, optional): Variables for the GraphQL query
        headers (dict, optional): HTTP headers to include
        jq_filter (str, optional): jq filter to apply to the result

    Returns:
        dict: The response data from the GraphQL API
    """
    # Set default headers if none provided
    if headers is None:
        headers = {
            "Content-Type": "application/json",
        }

    # Prepare the transport
    transport = RequestsHTTPTransport(
        url=endpoint_url,
        headers=headers,
        use_json=True,
    )

    # Create a client
    client = Client(transport=transport)

    # Parse the query string
    try:
        query = gql(query_string)
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse query: {e!s}"}

    try:
        result = client.execute(query, variable_values=variables)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    else:
        response = {"status": "success", "data": result}

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
                    "status": "success",
                    "data": response["data"],
                    "warning": f"jq filter failed: {jq_error!s}. "
                    "Tip: Use '// empty' or '// []' to handle null values. "
                    f"Example: '{jq_filter} // empty'",
                }

        return response
