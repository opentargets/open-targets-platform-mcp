"""Tool for providing example GraphQL queries for the OpenTargets API."""

import json
from pathlib import Path
from typing import Any

from otar_mcp.mcp_instance import mcp


def _get_extracted_queries_path() -> Path:
    """Get the absolute path to the extracted_queries directory."""
    # The tool is in src/otar_mcp/tools/examples.py
    # extracted_queries is at the project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "extracted_queries"


def _get_mappers_path() -> Path:
    """Get the absolute path to the mappers directory."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "mappers"


def _load_category_descriptors() -> dict[str, Any]:
    """Load category descriptors from JSON file."""
    mappers_path = _get_mappers_path()
    descriptors_file = mappers_path / "category_descriptors.json"
    with open(descriptors_file, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _load_category_query_mapper() -> dict[str, Any]:
    """Load category to query name mapping from JSON file."""
    mappers_path = _get_mappers_path()
    mapper_file = mappers_path / "category_query_mapper.json"
    with open(mapper_file, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _build_query_index() -> dict[str, Path]:
    """Build an index mapping query names to their file paths.

    Returns:
        Dictionary mapping query name (without .gql extension) to Path object
    """
    queries_dir = _get_extracted_queries_path()
    query_index = {}

    # Search all entity-type subdirectories for .gql files
    for entity_dir in queries_dir.iterdir():
        if entity_dir.is_dir() and not entity_dir.name.startswith((".", "__")):
            for gql_file in entity_dir.glob("*.gql"):
                query_name = gql_file.stem  # filename without extension
                query_index[query_name] = gql_file

    return query_index


def _clean_comment_line(line: str) -> str:
    """Remove comment marker from line."""
    return line[2:] if len(line) > 1 and line[1] == " " else line[1:]


def _parse_metadata_header(clean_line: str, metadata: dict) -> str | None:
    """Parse metadata header line and return current field or None.

    Args:
        clean_line: Cleaned comment line
        metadata: Metadata dictionary to update

    Returns:
        Current field name if multi-line, None otherwise
    """
    field_mappings = {
        "Query Name:": ("query_name", None),
        "Entity Type:": ("entity_type", None),
        "Description:": ("description", "description"),
        "Variables:": ("variables", "variables"),
        "Pagination Behavior:": ("pagination", None),
    }

    for prefix, (key, field) in field_mappings.items():
        if clean_line.startswith(prefix):
            value = clean_line.replace(prefix, "").strip()
            if value:
                metadata[key] = value
            return field

    return None


def _append_to_field(metadata: dict, field: str, text: str) -> None:
    """Append text to a metadata field."""
    if metadata[field]:
        metadata[field] += " " + text
    else:
        metadata[field] = text


def _parse_query_file(file_path: Path) -> dict:
    """Parse a .gql file and extract metadata and query content.

    Args:
        file_path: Path to the .gql file

    Returns:
        Dictionary with metadata fields and query string
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    metadata = {
        "query_name": "",
        "entity_type": "",
        "description": "",
        "variables": "",
        "pagination": "",
        "query": "",
    }

    lines = content.split("\n")
    query_lines = []
    in_query = False
    current_field = None

    for line in lines:
        if line.startswith("#"):
            clean_line = _clean_comment_line(line)

            if clean_line.strip() == "":
                current_field = None
            else:
                new_field = _parse_metadata_header(clean_line, metadata)
                if new_field is not None:
                    current_field = new_field
                elif current_field in ("description", "variables"):
                    _append_to_field(metadata, current_field, clean_line.strip())
        elif line.strip().startswith("query ") or in_query:
            in_query = True
            query_lines.append(line)

    metadata["query"] = "\n".join(query_lines).strip()
    return metadata


def _format_queries_as_markdown(queries_by_category: dict) -> str:
    """Format queries as markdown documentation.

    Args:
        queries_by_category: Dictionary mapping category names to lists of query metadata

    Returns:
        Markdown-formatted string
    """
    markdown_parts = []

    markdown_parts.append("# Open Targets GraphQL Query Examples\n")
    markdown_parts.append("This document contains example GraphQL queries organized by category.\n")

    for category, queries in queries_by_category.items():
        # Add category header
        markdown_parts.append(f"\n## {category.capitalize()} Queries\n")
        markdown_parts.append(f"\n**Total queries in this category:** {len(queries)}\n")

        # Add each query
        for query_data in queries:
            query_name = query_data.get("query_name", "Unknown")
            description = query_data.get("description", "")
            variables = query_data.get("variables", "")
            pagination = query_data.get("pagination", "")
            query_string = query_data.get("query", "")

            markdown_parts.append(f"\n### {query_name}\n")

            if description:
                markdown_parts.append(f"\n**Description:** {description}\n")

            if variables:
                markdown_parts.append(f"\n**Variables:** {variables}\n")

            if pagination:
                markdown_parts.append(f"\n**Pagination:** {pagination}\n")

            markdown_parts.append("\n**Query:**\n")
            markdown_parts.append(f"```graphql\n{query_string}\n```\n")

    return "\n".join(markdown_parts)


def _generate_docstring() -> str:
    """Generate the docstring dynamically from category descriptors."""
    try:
        category_descriptors = _load_category_descriptors()
    except Exception:
        # Fallback if descriptors can't be loaded
        return """Retrieve example GraphQL queries for the Open Targets API organized by category.

    Args:
        categories: List of category names to include.

    Returns:
        str: Markdown-formatted documentation containing all queries from the requested categories.
    """

    # Build category list from descriptors
    category_lines = []
    for category, info in sorted(category_descriptors.items()):
        description = info.get("description", "")
        category_lines.append(f"    - **{category}**: {description}")

    categories_text = "\n".join(category_lines)

    return f"""Retrieve example GraphQL queries for the Open Targets API organized by category.

    This tool loads query examples from the extracted_queries directory and formats them
    as comprehensive markdown documentation. The examples demonstrate common use cases
    and can be used as templates for writing custom queries.

    Available categories:
{categories_text}

    Args:
        categories: List of category names to include (e.g., ["clinical-genetics", "cancer-genomics"]).
                   Must be one or more of the available categories listed above.

    Returns:
        str: Markdown-formatted documentation containing all queries from the requested
             categories, with descriptions, variables, pagination info, and GraphQL code.

    Raises:
        ValueError: If an invalid category is provided or if no categories are specified
        FileNotFoundError: If required files or directories do not exist

    Example:
        >>> examples = get_open_targets_query_examples(["clinical-genetics", "cancer-genomics"])
        >>> # Returns markdown with all clinical genetics and cancer genomics query examples
    """


# Generate docstring at module load time (before decorator is applied)
_DYNAMIC_DOCSTRING = _generate_docstring()


def get_open_targets_query_examples(categories: list[str]) -> str:
    """Placeholder docstring - will be replaced dynamically."""
    # Load category information and mappings
    try:
        category_descriptors = _load_category_descriptors()
        category_query_mapper = _load_category_query_mapper()
    except FileNotFoundError as e:
        msg = f"Required mapper file not found: {e}"
        raise FileNotFoundError(msg) from e

    # Build query index (query name -> file path)
    query_index = _build_query_index()

    # Validate categories
    valid_categories = set(category_descriptors.keys())
    requested_categories = set(categories)
    invalid = requested_categories - valid_categories
    if invalid:
        valid_list = ", ".join(sorted(valid_categories))
        msg = f"Invalid categories: {invalid}. Valid categories are: {valid_list}"
        raise ValueError(msg)

    # Load queries for each requested category
    queries_by_category = {}

    for category in categories:
        # Get query names for this category from the mapper
        query_names = category_query_mapper.get(category, [])

        queries = []
        for query_name in query_names:
            # Look up the file path for this query
            query_file = query_index.get(query_name)

            if query_file is None:
                # Query name not found in any entity directory
                print(f"Warning: Query '{query_name}' not found in extracted_queries")
                continue

            try:
                query_data = _parse_query_file(query_file)
                queries.append(query_data)
            except Exception as e:
                # If parsing fails, skip this file but continue
                print(f"Warning: Failed to parse {query_file}: {e}")
                continue

        if queries:
            queries_by_category[category] = queries

    # Format as markdown
    markdown_output = _format_queries_as_markdown(queries_by_category)

    return markdown_output


# Set the dynamic docstring BEFORE applying the decorator
get_open_targets_query_examples.__doc__ = _DYNAMIC_DOCSTRING

# Now apply the decorator
get_open_targets_query_examples = mcp.tool(name="get_open_targets_query_examples")(get_open_targets_query_examples)  # type: ignore[assignment]
