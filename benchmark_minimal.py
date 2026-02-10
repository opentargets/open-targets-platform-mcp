#!/usr/bin/env python3
"""Minimal token usage benchmark - best case scenario."""

import asyncio
import json

import tiktoken

from open_targets_platform_mcp.tools import (
    get_type_details,
    search_schema,
)


def count_tokens(data: any) -> int:
    """Count tokens using tiktoken."""
    encoding = tiktoken.encoding_for_model("gpt-4")
    text = json.dumps(data, indent=2, default=str)
    return len(encoding.encode(text))


async def minimal_scenario():
    """Minimal token usage: User knows exactly what they want."""
    print("\n" + "=" * 80)
    print("MINIMAL RLM SCENARIO: User asks specific question")
    print("Question: 'Does the Target type have a field for cancer biomarkers?'")
    print("=" * 80)

    # Just search for "cancer" and get Target details
    print("\nStep 1: Search for 'cancer'")
    search_result = await search_schema("cancer", search_in=["field_names"])
    tokens1 = count_tokens(search_result)
    print(f"  Tokens: {tokens1}")
    print(f"  Matches: {search_result['total_matches']}")

    print("\nStep 2: Verify in Target type details")
    target_result = await get_type_details("Target")
    tokens2 = count_tokens(target_result)
    print(f"  Tokens: {tokens2}")
    print(f"  Fields: {len(target_result['fields'])}")

    total = tokens1 + tokens2
    print(f"\nTOTAL: {total:,} tokens")
    print(f"vs Full Schema: 24,424 tokens")
    print(f"Savings: {24424 - total:,} tokens ({(1 - total/24424)*100:.1f}%)")
    print(f"Efficiency: {24424/total:.1f}x more efficient")


async def query_only_scenario():
    """Even more minimal: Just get query fields."""
    print("\n" + "=" * 80)
    print("ULTRA-MINIMAL: Just list query entry points")
    print("Question: 'What query fields are available?'")
    print("=" * 80)

    from open_targets_platform_mcp.tools import list_schema_types

    result = await list_schema_types(type_filter=["query"])
    tokens = count_tokens(result)

    print(f"  Tokens: {tokens:,}")
    print(f"  Query fields: {len(result.get('query_fields', []))}")
    print(f"\nvs Full Schema: 24,424 tokens")
    print(f"Savings: {24424 - tokens:,} tokens ({(1 - tokens/24424)*100:.1f}%)")
    print(f"Efficiency: {24424/tokens:.1f}x more efficient")


if __name__ == "__main__":
    asyncio.run(minimal_scenario())
    asyncio.run(query_only_scenario())
