"""Tests for examples tool."""

import pytest

from otar_mcp.tools.examples import get_open_targets_query_examples


def test_get_open_targets_query_examples_returns_dict() -> None:
    """Test that get_open_targets_query_examples returns a dictionary."""
    result = get_open_targets_query_examples()
    assert isinstance(result, dict)
    assert len(result) > 0


def test_get_open_targets_query_examples_contains_expected_keys() -> None:
    """Test that examples contain expected query names."""
    result = get_open_targets_query_examples()
    expected_keys = [
        "informationForTargetByEnsemblId",
        "drugsForTargetByEnsemblId",
        "associatedDiseasesForTargetByEnsemblId",
    ]
    for key in expected_keys:
        assert key in result
