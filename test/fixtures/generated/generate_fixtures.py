"""Run this script once to capture real API responses into fixture files.

    uv run python test/fixtures/generated/generate_fixtures.py

Reads queries from queries.json in the same directory.
Writes:
  test/fixtures/generated/graphql_cassette.json  – stored query/response pairs
  test/fixtures/generated/schema.graphql          – full schema SDL

Both output files are auto-generated and must not be edited manually.
"""

import asyncio
import json
from pathlib import Path

from gql import Client, GraphQLRequest
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from graphql import print_ast, print_schema

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"
GENERATED_DIR = Path(__file__).parent
QUERIES_PATH = GENERATED_DIR / "queries.json"
CASSETTE_PATH = GENERATED_DIR / "graphql_cassette.json"
SCHEMA_SDL_PATH = GENERATED_DIR / "schema.graphql"

_COMMENT = (
    "AUTO-GENERATED — DO NOT EDIT MANUALLY. Regenerate with: uv run python test/fixtures/generated/generate_fixtures.py"
)


def _load_queries() -> list[dict]:
    with QUERIES_PATH.open() as f:
        return json.load(f)["queries"]


async def _run() -> None:
    transport = AIOHTTPTransport(
        url=API_URL,
        headers={"Content-Type": "application/json", "User-Agent": "otp-mcp-fixture-gen/0"},
        timeout=30,
    )

    queries = _load_queries()
    records: list[dict] = []

    # --- Data queries ---
    async with Client(transport=transport) as session:
        for entry in queries:
            label = entry["label"]
            query_str = entry["query"]
            variables = entry.get("variables")
            expect_error = entry.get("expect_error", False)

            print(f"Fetching: {label} ...", end=" ", flush=True)
            request = GraphQLRequest(query_str, variable_values=variables)
            try:
                response = await session.execute(request)
                if expect_error:
                    print(f"WARNING — expected error but got success: {json.dumps(response)[:120]}")
                else:
                    print("OK")
                    print(f"  result: {json.dumps(response)[:200]}")
                records.append(
                    {
                        "request": {"query": print_ast(request.document), "variables": variables},
                        "response": response,
                    },
                )
            except TransportQueryError as exc:
                if not expect_error:
                    print(f"WARNING — unexpected error: {exc}")
                else:
                    print("OK (error recorded)")
                records.append(
                    {
                        "request": {"query": print_ast(request.document), "variables": variables},
                        "response": {"_error": str(exc)},
                    },
                )

    cassette_doc = {"_comment": _COMMENT, "records": records}
    with CASSETTE_PATH.open("w") as f:
        json.dump(cassette_doc, f, indent=2)
    print(f"\nSaved cassette → {CASSETTE_PATH}")

    # --- Schema ---
    print("Fetching schema ...", end=" ", flush=True)
    schema_client = Client(transport=transport, fetch_schema_from_transport=True)
    async with schema_client:
        schema = schema_client.schema
        if schema is None:
            raise RuntimeError("Failed to fetch schema")
        sdl = print_schema(schema)
        SCHEMA_SDL_PATH.write_text(f"# {_COMMENT}\n\n{sdl}", encoding="utf-8")
    print("OK")
    print(f"Saved schema SDL → {SCHEMA_SDL_PATH}  ({len(sdl):,} chars)")


if __name__ == "__main__":
    asyncio.run(_run())
