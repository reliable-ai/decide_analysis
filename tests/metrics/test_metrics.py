"""
Snapshot tests for within- and between-bucket variation metrics.

Uses a minimal matrix so that the same data can be used in the companion
R tests (analysis/tests/testthat/test-new_methods.R) to verify that
both implementations produce equivalent estimates.

Example data
------------
dim_A  dim_B  dim_C  accuracy
a1     b1     c1     0.80
a1     b1     c2     0.82
a1     b2     c1     0.70
a1     b2     c2     0.73
a2     b1     c1     0.60
a2     b1     c2     0.63
a2     b2     c1     0.50
a2     b2     c2     0.55
"""

import pandas as pd

from src.metrics.metrics import (
    between_bucket_variation,
    organize_multiverse_results,
    within_bucket_variation,
)


def _make_example_multiverse():
    """Create a minimal 2×2×2 full-factorial multiverse result set."""
    data = pd.DataFrame({
        "dim_A": ["a1", "a1", "a1", "a1", "a2", "a2", "a2", "a2"],
        "dim_B": ["b1", "b1", "b2", "b2", "b1", "b1", "b2", "b2"],
        "dim_C": ["c1", "c2", "c1", "c2", "c1", "c2", "c1", "c2"],
        "accuracy": [0.80, 0.82, 0.70, 0.73, 0.60, 0.63, 0.50, 0.55],
    })
    return organize_multiverse_results(
        data,
        dimension_order=["dim_A", "dim_B", "dim_C"],
        performance_metrics=["accuracy"],
    )


def test_within_bucket_variation(snapshot):
    mv = _make_example_multiverse()
    result = within_bucket_variation(mv, "accuracy")
    rounded = {k: round(v, 10) for k, v in result.items()}
    assert rounded == snapshot


def test_between_bucket_variation(snapshot):
    mv = _make_example_multiverse()
    result = between_bucket_variation(mv, "accuracy")
    rounded = {k: round(v, 10) for k, v in result.items()}
    assert rounded == snapshot
