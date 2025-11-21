"""Tool for searching GraphQL query examples using BM25."""

import csv
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field
from rank_bm25 import BM25Okapi


def _get_queries_catalog_path() -> Path:
    """Get the absolute path to the queries_catalog.csv file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "extracted_queries" / "queries_catalog.csv"


def _get_query_file_path(entity_type: str, query_name: str) -> Path:
    """Get the absolute path to a .gql query file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    queries_dir = project_root / "extracted_queries"

    # Use query_name as filename (they match the .gql files)
    filename = f"{query_name}.gql"
    return queries_dir / entity_type / filename


def _load_queries_catalog() -> list[dict[str, str]]:
    """Load the queries catalog from CSV."""
    catalog_path = _get_queries_catalog_path()

    if not catalog_path.exists():
        msg = f"Queries catalog not found at {catalog_path}"
        raise FileNotFoundError(msg)

    queries: list[dict[str, str]] = []
    with open(catalog_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(dict(row))

    return queries


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase and split on whitespace and punctuation."""
    import re

    # Replace punctuation with spaces and split
    tokens = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return [t for t in tokens if t]  # Remove empty strings


def _build_bm25_index(queries: list[dict[str, str]]) -> tuple[Any, list[dict[str, str]]]:
    """Build BM25 index from query catalog.

    Index includes: query_name, description, keywords, entity_type.
    """
    documents = []
    for query in queries:
        # Combine all searchable fields
        searchable_text = " ".join([
            query.get("query_name", ""),
            query.get("description", ""),
            query.get("keywords", ""),
            query.get("entity_type", ""),
        ])
        documents.append(searchable_text)

    # Tokenize all documents
    tokenized_docs = [_tokenize(doc) for doc in documents]

    # Build BM25 index
    bm25 = BM25Okapi(tokenized_docs)

    return bm25, queries


def _search_with_multiple_queries(
    bm25: Any,
    queries_catalog: list[dict[str, str]],
    search_queries: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Search using multiple query variations and merge results.

    Args:
        bm25: The BM25 index
        queries_catalog: Full catalog of queries
        search_queries: Multiple phrasings of the same information need
        top_k: Number of results to return

    Returns:
        List of top_k query results with scores and matched_by info
    """
    # Track scores for each query in catalog
    query_scores: dict[int, dict] = {}  # index -> {score, matched_by: list[str]}

    for search_query in search_queries:
        tokenized_query = _tokenize(search_query)
        scores = bm25.get_scores(tokenized_query)

        # Aggregate scores
        for idx, score in enumerate(scores):
            if score > 0:  # Only consider non-zero scores
                if idx not in query_scores:
                    query_scores[idx] = {"score": 0.0, "matched_by": []}

                # Sum scores from different query variations
                query_scores[idx]["score"] += score
                query_scores[idx]["matched_by"].append(search_query)

    # Sort by score and get top_k
    sorted_results = sorted(
        query_scores.items(),
        key=lambda x: (len(x[1]["matched_by"]), x[1]["score"]),  # Boost by # of matches, then score
        reverse=True,
    )[:top_k]

    # Build result list with full query content
    results = []
    for idx, score_info in sorted_results:
        query_data: dict[str, Any] = queries_catalog[idx].copy()
        query_data["relevance_score"] = round(score_info["score"], 2)
        query_data["matched_by"] = score_info["matched_by"]
        query_data["match_count"] = len(score_info["matched_by"])

        # Load the actual query content from .gql file
        try:
            query_file = _get_query_file_path(
                query_data["entity_type"],
                query_data["query_name"],
            )
            if query_file.exists():
                with open(query_file, encoding="utf-8") as f:
                    query_data["query_content"] = f.read()
            else:
                query_data["query_content"] = f"[Query file not found: {query_file}]"
        except Exception as e:
            query_data["query_content"] = f"[Error loading query: {e}]"

        results.append(query_data)

    return results


def _format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results as markdown."""
    if not results:
        return "No matching queries found."

    markdown_parts = [
        "# Query Search Results\n",
        f"Found {len(results)} relevant queries:\n",
    ]

    for i, result in enumerate(results, 1):
        markdown_parts.append(f"\n## {i}. {result['query_name']}\n")
        markdown_parts.append(f"**Entity Type:** {result['entity_type']}\n")
        markdown_parts.append(f"**Relevance Score:** {result['relevance_score']}\n")
        markdown_parts.append(f"**Matched by {result['match_count']} search variation(s):**\n")
        for matched_query in result["matched_by"]:
            markdown_parts.append(f'  - "{matched_query}"\n')

        if result.get("description"):
            markdown_parts.append(f"\n**Description:** {result['description']}\n")

        if result.get("variables"):
            markdown_parts.append(f"\n**Variables:** {result['variables']}\n")

        if result.get("pagination_behavior"):
            markdown_parts.append(f"\n**Pagination:** {result['pagination_behavior']}\n")

        markdown_parts.append("\n**Query:**\n")
        markdown_parts.append(f"```graphql\n{result.get('query_content', '[No content]')}\n```\n")

    return "".join(markdown_parts)


# Initialize BM25 index at module load time
_bm25_index: Any = None
_queries_catalog: list[dict[str, str]] | None = None


def _get_or_initialize_index() -> tuple[Any, list[dict[str, str]]]:
    """Get or initialize the BM25 index (lazy loading with caching)."""
    global _bm25_index, _queries_catalog

    if _bm25_index is None or _queries_catalog is None:
        _queries_catalog = _load_queries_catalog()
        _bm25_index, _queries_catalog = _build_bm25_index(_queries_catalog)

    return _bm25_index, _queries_catalog


# @mcp.tool(name="search_query_examples")
def search_query_examples(
    search_queries: Annotated[
        list[str],
        Field(
            description="3-5 diverse search queries describing the same information need from different angles",
            min_length=3,
            max_length=5,
        ),
    ],
    top_k: Annotated[
        int,
        Field(description="Number of query examples to return", ge=1, le=20),
    ] = 5,
) -> str:
    """Search for relevant GraphQL query examples using BM25 lexical search.

    Provide 3-5 diverse phrasings of the same information need. Results matched by
    multiple queries rank higher.

    Args:
        search_queries: 3-5 diverse phrasings of the same information need (minimum 3 required)
        top_k: Number of query examples to return (default: 5)

    Returns:
        Markdown-formatted results with query content, descriptions, and relevance scores
    """
    if len(search_queries) < 3:
        return "Error: Please provide at least 3 search queries to ensure good coverage."

    if len(search_queries) > 5:
        return "Error: Maximum 5 search queries allowed."

    try:
        # Get or initialize BM25 index
        bm25, queries_catalog = _get_or_initialize_index()

        # Search with multiple queries
        results = _search_with_multiple_queries(
            bm25,
            queries_catalog,
            search_queries,
            top_k,
        )

        # Format and return
        return _format_search_results(results)

    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error searching queries: {e}"
