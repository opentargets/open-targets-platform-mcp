"""Tool for semantic search of GraphQL query examples using embedding models."""

import csv
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

# Optional dependencies for semantic search
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False


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


def _load_query_content(entity_type: str, query_name: str) -> str:
    """Load the content of a .gql query file."""
    query_file = _get_query_file_path(entity_type, query_name)
    if query_file.exists():
        with open(query_file, encoding="utf-8") as f:
            return f.read()
    return ""


def _load_embedding_model() -> Any:
    """Load the EmbeddingGemma model."""
    if not SEMANTIC_SEARCH_AVAILABLE:
        msg = "Semantic search dependencies not available"
        raise ImportError(msg)
    model_name = "google/embeddinggemma-300m"
    model = SentenceTransformer(model_name)
    return model


def _format_document(title: str, content: str) -> str:
    """Format a document with the proper task prefix for EmbeddingGemma.

    According to the model card, documents should use the format:
    "title: {title | 'none'} | text: {content}"
    """
    # Clean up title and content
    title_clean = title.strip() if title else "none"
    content_clean = content.strip()

    # Combine with proper format
    document_text = " ".join([title_clean, content_clean])

    return f"title: {title_clean} | text: {document_text}"


def _format_query(query_text: str) -> str:
    """Format a query with the proper task prefix for EmbeddingGemma.

    According to the model card, queries should use the format:
    "task: search result | query: {content}"
    """
    return f"task: search result | query: {query_text}"


def _get_embeddings_path() -> Path:
    """Get the path to the pre-computed embeddings file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "extracted_queries" / "query_embeddings.npy"


def _load_precomputed_embeddings() -> tuple[list[dict[str, Any]], Any]:
    """Load pre-computed embeddings from disk.

    Returns:
        Tuple of (queries_catalog, embeddings_array)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        msg = "Semantic search dependencies not available"
        raise ImportError(msg)

    queries_catalog = _load_queries_catalog()
    embeddings_path = _get_embeddings_path()

    if not embeddings_path.exists():
        msg = (
            f"Pre-computed embeddings not found at {embeddings_path}. "
            "Run: python extracted_queries/precompute_embeddings.py"
        )
        raise FileNotFoundError(msg)

    # Load embeddings from disk
    embeddings = np.load(embeddings_path)

    # Verify dimensions match
    if len(queries_catalog) != len(embeddings):
        msg = (
            f"Embedding count mismatch: {len(embeddings)} embeddings "
            f"vs {len(queries_catalog)} queries. Re-run precompute_embeddings.py"
        )
        raise ValueError(msg)

    return queries_catalog, embeddings


def _semantic_search(
    query_text: str,
    model: Any,
    queries_catalog: list[dict[str, Any]],
    embeddings_array: Any,
    top_k: int,
) -> list[dict[str, Any]]:
    """Perform semantic search using embeddings.

    Args:
        query_text: The search query
        model: The embedding model
        queries_catalog: Catalog of queries
        embeddings_array: Pre-computed embeddings array
        top_k: Number of results to return

    Returns:
        List of top_k results with similarity scores
    """
    # Format and embed the query
    formatted_query = _format_query(query_text)
    query_embedding = model.encode([formatted_query], convert_to_numpy=True)[0]

    # Calculate cosine similarities
    # Normalize vectors for cosine similarity
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    docs_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)

    # Compute similarities
    similarities = np.dot(docs_norm, query_norm)

    # Get top k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Build result list with full query content
    results = []
    for idx in top_indices:
        query_data: dict[str, Any] = queries_catalog[idx].copy()
        query_data["similarity_score"] = round(float(similarities[idx]), 4)

        # Load the actual query content from .gql file
        try:
            query_file = _get_query_file_path(query_data["entity_type"], query_data["query_name"])
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
        "# Semantic Query Search Results\n",
        f"Found {len(results)} relevant queries:\n",
    ]

    for i, result in enumerate(results, 1):
        markdown_parts.append(f"\n## {i}. {result['query_name']}\n")
        markdown_parts.append(f"**Entity Type:** {result['entity_type']}\n")
        markdown_parts.append(f"**Similarity Score:** {result['similarity_score']:.4f}\n")

        if result.get("description"):
            markdown_parts.append(f"\n**Description:** {result['description']}\n")

        if result.get("variables"):
            markdown_parts.append(f"\n**Variables:** {result['variables']}\n")

        if result.get("pagination_behavior"):
            markdown_parts.append(f"\n**Pagination:** {result['pagination_behavior']}\n")

        markdown_parts.append("\n**Query:**\n")
        markdown_parts.append(f"```graphql\n{result.get('query_content', '[No content]')}\n```\n")

    return "".join(markdown_parts)


# Global cache for model and embeddings
_model: Any = None
_queries_catalog: list[dict[str, Any]] | None = None
_embeddings_array: Any = None


def _get_or_initialize_semantic_index() -> tuple[Any, list[dict[str, Any]], Any]:
    """Get or initialize the semantic search index (lazy loading with caching)."""
    global _model, _queries_catalog, _embeddings_array

    if _model is None or _queries_catalog is None or _embeddings_array is None:
        _model = _load_embedding_model()
        _queries_catalog, _embeddings_array = _load_precomputed_embeddings()

    return _model, _queries_catalog, _embeddings_array


# @mcp.tool(name="semantic_search_query_examples")
def semantic_search_query_examples(
    search_query: Annotated[
        str,
        Field(description="Natural language search query describing the information you need"),
    ],
    top_k: Annotated[
        int,
        Field(description="Number of query examples to return", ge=1, le=20),
    ] = 5,
) -> str:
    """Search for relevant GraphQL query examples using semantic similarity.

    Uses EmbeddingGemma-300M to find queries with similar meaning.

    Args:
        search_query: Natural language description of what you're looking for
        top_k: Number of query examples to return (default: 5)

    Returns:
        Markdown-formatted results with query content, descriptions, and similarity scores

    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        return (
            "Error: Semantic search requires optional dependencies. "
            "Install with: uv pip install 'otar-mcp[semantic]' or uv add --optional semantic sentence-transformers"
        )

    try:
        # Get or initialize semantic index
        model, queries_catalog, embeddings_array = _get_or_initialize_semantic_index()

        # Perform semantic search
        results = _semantic_search(search_query, model, queries_catalog, embeddings_array, top_k)

        # Format and return
        return _format_search_results(results)

    except FileNotFoundError as e:
        return f"Error: {e}"
    except ImportError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error performing semantic search: {e}"
