#!/usr/bin/env python3
"""Benchmark script to compare token usage: Old schema dump vs RLM approach."""

import asyncio
from typing import Any

import tiktoken

from open_targets_platform_mcp.tools import (
    get_open_targets_graphql_schema,
    get_type_details,
    list_schema_types,
    search_schema,
)


def count_tokens(text: str | dict | list, model: str = "gpt-4") -> int:
    """Count tokens in text or JSON response using tiktoken.

    Args:
        text: Text string or dict/list to count tokens for
        model: Model name for tokenizer (default: gpt-4)

    Returns:
        Number of tokens
    """
    encoding = tiktoken.encoding_for_model(model)

    # Convert dict/list to JSON string
    if isinstance(text, (dict, list)):
        import json

        # Custom handler for non-serializable objects (like GraphQL UndefinedType)
        def json_default(obj):
            if hasattr(obj, '__class__'):
                return str(obj)
            return None

        text = json.dumps(text, indent=2, default=json_default)

    return len(encoding.encode(text))


async def benchmark_old_approach() -> dict[str, Any]:
    """Benchmark the old approach: dump entire schema."""
    print("\n" + "=" * 80)
    print("OLD APPROACH: Full Schema Dump")
    print("=" * 80)

    schema_sdl = await get_open_targets_graphql_schema()
    tokens = count_tokens(schema_sdl)

    print(f"✓ Called: get_open_targets_graphql_schema()")
    print(f"  Response length: {len(schema_sdl):,} characters")
    print(f"  Token count: {tokens:,} tokens")

    return {
        "approach": "old",
        "tools_called": ["get_open_targets_graphql_schema"],
        "total_tokens": tokens,
        "response_size": len(schema_sdl),
    }


async def benchmark_rlm_scenario_1() -> dict[str, Any]:
    """Benchmark RLM approach: Simple query construction.

    Scenario: User asks "What information is available about genes?"
    """
    print("\n" + "=" * 80)
    print("RLM APPROACH - Scenario 1: Simple Query Construction")
    print("Use case: User asks 'What information is available about genes?'")
    print("=" * 80)

    total_tokens = 0
    tools_called = []
    responses = []

    # Step 1: Get overview
    print("\nStep 1: Get overview of schema types")
    result1 = await list_schema_types(type_filter=["query", "object"])
    tokens1 = count_tokens(result1)
    total_tokens += tokens1
    tools_called.append("list_schema_types(['query', 'object'])")
    responses.append(result1)
    print(f"✓ list_schema_types(['query', 'object'])")
    print(f"  Token count: {tokens1:,} tokens")
    print(f"  Found {len(result1.get('query_fields', []))} query fields, {len(result1.get('object_types', []))} object types")

    # Step 2: Get details for Target type
    print("\nStep 2: Get details for Target type")
    result2 = await get_type_details("Target")
    tokens2 = count_tokens(result2)
    total_tokens += tokens2
    tools_called.append("get_type_details('Target')")
    responses.append(result2)
    print(f"✓ get_type_details('Target')")
    print(f"  Token count: {tokens2:,} tokens")
    print(f"  Found {len(result2.get('fields', []))} fields")

    print(f"\n{'─' * 80}")
    print(f"TOTAL TOKENS: {total_tokens:,}")
    print(f"Tools called: {len(tools_called)}")

    return {
        "approach": "rlm_scenario_1",
        "tools_called": tools_called,
        "total_tokens": total_tokens,
        "steps": len(tools_called),
        "responses": responses,
    }


async def benchmark_rlm_scenario_2() -> dict[str, Any]:
    """Benchmark RLM approach: Complex nested query.

    Scenario: User asks "Find cancer-related data for a gene"
    """
    print("\n" + "=" * 80)
    print("RLM APPROACH - Scenario 2: Complex Nested Query")
    print("Use case: User asks 'Find cancer-related data for a gene'")
    print("=" * 80)

    total_tokens = 0
    tools_called = []
    responses = []

    # Step 1: Search for cancer-related fields
    print("\nStep 1: Search for cancer-related fields")
    result1 = await search_schema("cancer", search_in=["field_names", "type_names"])
    tokens1 = count_tokens(result1)
    total_tokens += tokens1
    tools_called.append("search_schema('cancer', ['field_names', 'type_names'])")
    responses.append(result1)
    print(f"✓ search_schema('cancer')")
    print(f"  Token count: {tokens1:,} tokens")
    print(f"  Found {result1.get('total_matches', 0)} matches")

    # Step 2: Get details for Target type
    print("\nStep 2: Get details for Target type")
    result2 = await get_type_details("Target")
    tokens2 = count_tokens(result2)
    total_tokens += tokens2
    tools_called.append("get_type_details('Target')")
    responses.append(result2)
    print(f"✓ get_type_details('Target')")
    print(f"  Token count: {tokens2:,} tokens")

    # Step 3: Get details for CancerBiomarker type (nested)
    print("\nStep 3: Get details for CancerBiomarker type (nested)")
    result3 = await get_type_details("Disease")
    tokens3 = count_tokens(result3)
    total_tokens += tokens3
    tools_called.append("get_type_details('Disease')")
    responses.append(result3)
    print(f"✓ get_type_details('Disease')")
    print(f"  Token count: {tokens3:,} tokens")

    print(f"\n{'─' * 80}")
    print(f"TOTAL TOKENS: {total_tokens:,}")
    print(f"Tools called: {len(tools_called)}")

    return {
        "approach": "rlm_scenario_2",
        "tools_called": tools_called,
        "total_tokens": total_tokens,
        "steps": len(tools_called),
        "responses": responses,
    }


async def run_benchmark():
    """Run all benchmarks and compare results."""
    print("\n" + "=" * 80)
    print("BENCHMARKING: Token Usage Comparison")
    print("Old Schema Dump vs RLM-based Incremental Discovery")
    print("=" * 80)

    # Run benchmarks
    old_result = await benchmark_old_approach()
    rlm_result_1 = await benchmark_rlm_scenario_1()
    rlm_result_2 = await benchmark_rlm_scenario_2()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY: Token Usage Comparison")
    print("=" * 80)

    old_tokens = old_result["total_tokens"]
    rlm_tokens_1 = rlm_result_1["total_tokens"]
    rlm_tokens_2 = rlm_result_2["total_tokens"]

    print(f"\nOld Approach (Full Schema Dump):")
    print(f"  Total tokens: {old_tokens:,}")
    print(f"  Tools called: 1")
    print(f"  Response size: {old_result['response_size']:,} characters")

    print(f"\nRLM Approach - Scenario 1 (Simple):")
    print(f"  Total tokens: {rlm_tokens_1:,}")
    print(f"  Tools called: {rlm_result_1['steps']}")
    print(f"  Token reduction: {old_tokens - rlm_tokens_1:,} ({(1 - rlm_tokens_1/old_tokens)*100:.1f}%)")
    print(f"  Efficiency: {old_tokens / rlm_tokens_1:.1f}x more efficient")

    print(f"\nRLM Approach - Scenario 2 (Complex):")
    print(f"  Total tokens: {rlm_tokens_2:,}")
    print(f"  Tools called: {rlm_result_2['steps']}")
    print(f"  Token reduction: {old_tokens - rlm_tokens_2:,} ({(1 - rlm_tokens_2/old_tokens)*100:.1f}%)")
    print(f"  Efficiency: {old_tokens / rlm_tokens_2:.1f}x more efficient")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print(f"RLM approach saves {(1 - max(rlm_tokens_1, rlm_tokens_2)/old_tokens)*100:.1f}% tokens")
    print(f"Even complex scenarios use {max(rlm_tokens_1, rlm_tokens_2):,} tokens vs {old_tokens:,}")
    print(f"Context pollution reduced by {old_tokens / max(rlm_tokens_1, rlm_tokens_2):.1f}x")
    print()

    return {
        "old": old_result,
        "rlm_scenario_1": rlm_result_1,
        "rlm_scenario_2": rlm_result_2,
    }


if __name__ == "__main__":
    asyncio.run(run_benchmark())
