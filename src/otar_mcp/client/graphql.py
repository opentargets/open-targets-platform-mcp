from gql import Client, gql  # type: ignore
from gql.transport.requests import RequestsHTTPTransport  # type: ignore
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
            raise ValueError("Failed to fetch schema from the GraphQL endpoint.")

        return client.schema


def execute_graphql_query(endpoint_url, query_string, variables=None, headers=None) -> dict:
    """Make a generic GraphQL API call.

    Args:
        endpoint_url (str): The GraphQL endpoint URL
        query_string (str): The GraphQL query or mutation as a string
        variables (dict, optional): Variables for the GraphQL query
        headers (dict, optional): HTTP headers to include

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
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}