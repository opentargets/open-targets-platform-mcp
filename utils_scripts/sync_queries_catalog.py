#!/usr/bin/env python3
"""
Script to sync query names from .gql files with queries_catalog.csv
Ensures 1:1 mapping between query files and catalog entries.
"""

import argparse
import csv
import os
import re
from datetime import datetime
from pathlib import Path


def extract_query_name_from_file(file_path):
    """Extract the query name from a .gql file by parsing the query definition."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Look for query name in the query definition (query QueryName(...))
    # This pattern matches: query <QueryName>( or query <QueryName> {
    pattern = r"query\s+([A-Za-z0-9_]+)\s*[\(\{]"
    match = re.search(pattern, content)

    if match:
        return match.group(1)

    # If no match found, try to extract from comment header
    header_pattern = r"#\s*Query Name:\s*([A-Za-z0-9_]+)"
    match = re.search(header_pattern, content)

    if match:
        return match.group(1)

    return None


def find_all_gql_files(queries_dir):
    """Recursively find all .gql files in the queries directory."""
    queries_path = Path(queries_dir)
    gql_files = []

    for file_path in queries_path.rglob("*.gql"):
        # Skip the schema file
        if file_path.name == "schema.graphql" or file_path.name == "schema.gql":
            continue
        gql_files.append(file_path)

    return gql_files


def extract_query_names_from_files(queries_dir):
    """Extract all query names from .gql files."""
    gql_files = find_all_gql_files(queries_dir)
    query_mapping = {}

    for file_path in gql_files:
        query_name = extract_query_name_from_file(file_path)
        if query_name:
            query_mapping[query_name] = str(file_path)
        else:
            print(f"⚠️  Warning: Could not extract query name from {file_path}")

    return query_mapping


def read_csv_catalog(csv_path):
    """Read the queries_catalog.csv and return query names."""
    query_names = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query_names.append(row["query_name"])

    return query_names


def backup_csv(csv_path):
    """Create a backup of the CSV file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{csv_path}.backup.{timestamp}"

    with open(csv_path, encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    print(f"✅ Backup created: {backup_path}")
    return backup_path


def sync_catalog(queries_dir, csv_path, dry_run=False):
    """
    Sync the catalog CSV with actual query files.

    Args:
        queries_dir: Path to the extracted_queries directory
        csv_path: Path to the queries_catalog.csv file
        dry_run: If True, only report differences without making changes
    """
    print(f"🔍 Scanning for .gql files in {queries_dir}")
    file_queries = extract_query_names_from_files(queries_dir)
    print(f"📁 Found {len(file_queries)} query files")

    print(f"\n🔍 Reading catalog from {csv_path}")
    csv_queries = set(read_csv_catalog(csv_path))
    print(f"📊 Found {len(csv_queries)} entries in catalog")

    # Compare
    file_query_set = set(file_queries.keys())

    missing_in_csv = file_query_set - csv_queries
    exceeding_in_csv = csv_queries - file_query_set
    matched = file_query_set & csv_queries

    print("\n📈 Sync Analysis:")
    print(f"  ✅ Matched queries: {len(matched)}")
    print(f"  ❌ Missing in CSV (exist in files): {len(missing_in_csv)}")
    print(f"  ❌ Exceeding in CSV (no file found): {len(exceeding_in_csv)}")

    if missing_in_csv:
        print("\n⚠️  Queries missing in CSV:")
        for query_name in sorted(missing_in_csv):
            print(f"    - {query_name}")
            print(f"      File: {file_queries[query_name]}")

    if exceeding_in_csv:
        print("\n⚠️  Queries in CSV without corresponding files:")
        for query_name in sorted(exceeding_in_csv):
            print(f"    - {query_name}")

    # Perform sync if not dry run
    if not dry_run and (missing_in_csv or exceeding_in_csv):
        print("\n🔄 Syncing catalog...")

        # Backup first
        backup_csv(csv_path)

        # Read all rows
        rows = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                # Only keep rows that have matching files
                if row["query_name"] in file_query_set:
                    rows.append(row)

        # Add missing queries with placeholder data
        for query_name in missing_in_csv:
            rows.append({
                "query_name": query_name,
                "entity_type": "TODO",
                "source_file": file_queries[query_name].replace(queries_dir + "/", ""),
                "description": "TODO: Add description",
                "keywords": "",
                "variables": "",
                "tested_status": "⏳ Not tested",
                "pagination_behavior": "",
                "notes": "Auto-added by sync script",
            })

        # Write back
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print("✅ Catalog synced successfully!")
        print(f"  - Removed {len(exceeding_in_csv)} exceeding entries")
        print(f"  - Added {len(missing_in_csv)} missing entries (with TODO placeholders)")
        print(f"  - Total entries in catalog: {len(rows)}")
    elif dry_run:
        print("\n🔍 Dry run mode - no changes made")
        print("   Run without --dry-run to apply changes")
    else:
        print("\n✅ Catalog is already in sync!")

    return {"matched": matched, "missing_in_csv": missing_in_csv, "exceeding_in_csv": exceeding_in_csv}


def main():
    parser = argparse.ArgumentParser(description="Sync query names from .gql files with queries_catalog.csv")
    parser.add_argument(
        "--queries-dir",
        default="/Users/carli/Projects/otar-official-mcp/extracted_queries",
        help="Path to the extracted_queries directory",
    )
    parser.add_argument(
        "--catalog",
        default="/Users/carli/Projects/otar-official-mcp/extracted_queries/queries_catalog.csv",
        help="Path to the queries_catalog.csv file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only report differences without making changes")

    args = parser.parse_args()

    # Ensure paths exist
    if not os.path.exists(args.queries_dir):
        print(f"❌ Error: Queries directory not found: {args.queries_dir}")
        return 1

    if not os.path.exists(args.catalog):
        print(f"❌ Error: Catalog CSV not found: {args.catalog}")
        return 1

    sync_catalog(args.queries_dir, args.catalog, args.dry_run)
    return 0


if __name__ == "__main__":
    exit(main())
