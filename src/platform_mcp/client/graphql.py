from typing import Any

import jq
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


def execute_graphql_query(
    endpoint_url: str,
    query_string: str,
    variables: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    jq_filter: str | None = None,
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
                    return {"result": single_result}
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
