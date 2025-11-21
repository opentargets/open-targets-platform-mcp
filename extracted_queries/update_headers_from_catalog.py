#!/usr/bin/env python3
"""
Updates GraphQL query file headers with metadata from queries_catalog.csv.

This script:
1. Removes existing header comments from .gql files
2. Adds new header comments based on CSV catalog metadata
3. Is rerunnable - can update/replace existing annotations
4. Processes all .gql files recursively in extracted_queries directory

Usage: python update_headers_from_catalog.py

To customize which columns are included in the header annotations,
modify the ANNOTATION_COLUMNS list below.
"""

import csv
import sys
from datetime import date
from pathlib import Path

# ============================================================================
# CONFIGURATION: Customize which CSV columns to include in annotations
# ============================================================================
# Add or remove column names here to control what appears in the header.
# The order matters - columns will appear in this order in the header.
# Set to None or empty list to skip annotations from CSV altogether.
ANNOTATION_COLUMNS = [
    "entity_type",
    # "source_file",
    "description",
    "variables",
    # "keywords",
    # "tested_status",
    "pagination_behavior",
    "notes",
]

# Column that contains the query name (used for matching .gql files)
QUERY_NAME_COLUMN = "query_name"

# ============================================================================


def load_catalog(csv_path):
    """Load the queries catalog CSV into a dictionary keyed by query_name."""
    catalog = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query_name = row.get(QUERY_NAME_COLUMN)
            if query_name:
                catalog[query_name] = row

    return catalog


def extract_query_name(gql_content):
    """
    Extract the query or fragment name from the GraphQL content.
    Looks for patterns like:
    - query QueryName(...)
    - fragment FragmentName on ...
    """
    lines = gql_content.strip().split("\n")

    for line in lines:
        stripped = line.strip()

        # Skip comments
        if stripped.startswith("#"):
            continue

        # Look for query or fragment definitions
        if stripped.startswith("query ") or stripped.startswith("fragment "):
            # Extract name (word after 'query' or 'fragment')
            parts = stripped.split()
            if len(parts) >= 2:
                # Remove any opening parenthesis or 'on' keyword
                name = parts[1].split("(")[0].split()[0]
                return name

    return None


def remove_header_comments(gql_content):
    """
    Remove all comment lines from the beginning of the file.
    Returns the content without leading comments.
    """
    lines = gql_content.split("\n")

    # Find the first non-comment, non-empty line
    first_code_line_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_code_line_idx = i
            break

    # Return content from first code line onward
    return "\n".join(lines[first_code_line_idx:])


def format_value(value):
    """Format a CSV value for display in comments."""
    if not value or value.strip() == "":
        return None
    return value.strip()


def generate_header_comment(query_name, metadata):
    """
    Generate header comment from catalog metadata.
    Only includes columns specified in ANNOTATION_COLUMNS.
    """
    lines = []
    lines.append(f"# Query Name: {query_name}")

    for column in ANNOTATION_COLUMNS:
        if column not in metadata:
            continue

        value = format_value(metadata[column])
        if not value:
            continue

        # Format column name for display (convert snake_case to Title Case)
        display_name = column.replace("_", " ").title()

        # Handle multiline values (like description)
        if "\n" in value or len(value) > 80:
            lines.append(f"# {display_name}:")
            # Split long text into multiple comment lines
            words = value.split()
            current_line = "#"
            for word in words:
                if len(current_line) + len(word) + 1 > 78:  # Max line length
                    lines.append(current_line)
                    current_line = "#  " + word
                else:
                    current_line += " " + word
            if current_line.strip() != "#":
                lines.append(current_line)
        else:
            lines.append(f"# {display_name}: {value}")

    # Add extraction date
    lines.append("#")
    lines.append(f"# Last Updated: {date.today().isoformat()}")
    lines.append("")  # Empty line before query

    return "\n".join(lines)


def update_gql_file(gql_path, catalog):
    """Update a single .gql file with catalog metadata."""
    # Read current content
    with open(gql_path, encoding="utf-8") as f:
        content = f.read()

    # Remove existing header comments
    code_content = remove_header_comments(content)

    # Extract query name from the GraphQL code
    query_name = extract_query_name(code_content)

    if not query_name:
        print(f"  ⚠️  Could not extract query name from {gql_path.name}")
        return False

    # Look up metadata in catalog
    if query_name not in catalog:
        print(f"  ⚠️  No catalog entry found for {query_name}")
        # Still write the file without catalog metadata, just cleaned up
        with open(gql_path, "w", encoding="utf-8") as f:
            f.write(f"# Query Name: {query_name}\n")
            f.write("# (No catalog entry found)\n")
            f.write("#\n")
            f.write(f"# Last Updated: {date.today().isoformat()}\n\n")
            f.write(code_content)
        return False

    # Generate new header
    header = generate_header_comment(query_name, catalog[query_name])

    # Write updated file
    with open(gql_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(code_content)

    return True


def find_gql_files(root_dir):
    """Find all .gql files in the directory and subdirectories."""
    root_path = Path(root_dir)
    return sorted(root_path.rglob("*.gql"))


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent

    # Paths
    catalog_path = script_dir / "queries_catalog.csv"

    if not catalog_path.exists():
        print(f"❌ Error: Catalog file not found at {catalog_path}")
        sys.exit(1)

    # Load catalog
    print(f"📖 Loading catalog from {catalog_path.name}...")
    catalog = load_catalog(catalog_path)
    print(f"   Found {len(catalog)} entries in catalog\n")

    # Find all .gql files
    gql_files = find_gql_files(script_dir)

    if not gql_files:
        print("No .gql files found in the directory")
        return

    print(f"🔍 Found {len(gql_files)} .gql files to process\n")
    print(f"📝 Using annotation columns: {', '.join(ANNOTATION_COLUMNS)}\n")
    print("=" * 60)

    success_count = 0
    warning_count = 0
    error_count = 0

    for gql_file in gql_files:
        relative_path = gql_file.relative_to(script_dir)
        print(f"\n📄 Processing {relative_path}")

        try:
            if update_gql_file(gql_file, catalog):
                print("   ✅ Successfully updated")
                success_count += 1
            else:
                warning_count += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            error_count += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("Processing complete!\n")
    print(f"✅ Successfully updated: {success_count} files")
    if warning_count > 0:
        print(f"⚠️  Warnings: {warning_count} files")
    if error_count > 0:
        print(f"❌ Errors: {error_count} files")
    print(f"{'=' * 60}\n")

    if warning_count > 0 or error_count > 0:
        print("💡 Tip: Check warnings above for queries not found in catalog")


if __name__ == "__main__":
    main()
