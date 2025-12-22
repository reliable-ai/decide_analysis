import pandas as pd
import numpy as np
import pytest
from src.data_cleaning.missing_values import (
    replace_missing_value_placeholder,
    handle_missing_values,
)


class TestReplaceMissingValuePlaceholder:
    """Tests for replace_missing_value_placeholder function."""

    def test_replace_default_placeholder(self):
        """Test replacing default placeholder value (99999) with NaN."""
        df = pd.DataFrame({"a": [1, 99999, 3], "b": [99999, 5, 6]})

        result = replace_missing_value_placeholder(df)

        assert pd.isna(result.loc[1, "a"])
        assert pd.isna(result.loc[0, "b"])
        assert result.loc[0, "a"] == 1
        assert result.loc[1, "b"] == 5

    def test_replace_custom_placeholder(self):
        """Test replacing custom placeholder value with NaN."""
        df = pd.DataFrame({"a": [1, -999, 3], "b": [-999, 5, 6]})

        result = replace_missing_value_placeholder(df, placeholder=-999)

        assert pd.isna(result.loc[1, "a"])
        assert pd.isna(result.loc[0, "b"])
        assert result.loc[0, "a"] == 1

    def test_no_placeholders_present(self):
        """Test with DataFrame that has no placeholder values."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = replace_missing_value_placeholder(df)

        pd.testing.assert_frame_equal(result, df)

    def test_all_placeholders(self):
        """Test with DataFrame where all values are placeholders."""
        df = pd.DataFrame({"a": [99999, 99999], "b": [99999, 99999]})

        result = replace_missing_value_placeholder(df)

        assert result.isna().all().all()


class TestHandleMissingValues:
    """Tests for handle_missing_values function."""

    def test_drop_columns_threshold(self):
        """Test dropping columns with missing values above threshold."""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [1, np.nan, np.nan, np.nan, 5],  # 60% missing
                "c": [1, 2, np.nan, 4, 5],  # 20% missing
            }
        )

        strategy = [{"drop_columns": 0.5}]
        result = handle_missing_values(df, strategy)

        assert "a" in result.columns
        assert "c" in result.columns
        assert "b" not in result.columns

    def test_drop_columns_no_drops(self):
        """Test drop_columns when no columns exceed threshold."""
        df = pd.DataFrame(
            {"a": [1, 2, 3], "b": [1, 2, 3], "c": [1, np.nan, 3]}  # 33% missing
        )

        strategy = [{"drop_columns": 0.5}]
        result = handle_missing_values(df, strategy)

        assert list(result.columns) == ["a", "b", "c"]

    def test_drop_rows_subset(self):
        """Test dropping rows with missing values in specified columns."""
        df = pd.DataFrame(
            {
                "a": [1, np.nan, 3, 4],
                "b": [1, 2, np.nan, 4],
                "c": [1, 2, 3, np.nan],
            }
        )

        strategy = [{"drop_rows": ["a", "b"]}]
        result = handle_missing_values(df, strategy)

        assert len(result) == 2  # Only rows 0 and 3 remain
        assert result.index.tolist() == [0, 3]

    def test_drop_rows_invalid_column(self):
        """Test drop_rows with non-existent column name."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"drop_rows": ["nonexistent"]}]

        with pytest.raises(ValueError, match="Columns not found"):
            handle_missing_values(df, strategy)

    def test_impute_mean(self):
        """Test imputation with mean strategy."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0, 4.0]})

        strategy = [{"impute": {"a": "mean"}}]
        result = handle_missing_values(df, strategy)

        expected_mean = (1.0 + 3.0 + 4.0) / 3
        assert result.loc[1, "a"] == pytest.approx(expected_mean)

    def test_impute_median(self):
        """Test imputation with median strategy."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0, 10.0]})

        strategy = [{"impute": {"a": "median"}}]
        result = handle_missing_values(df, strategy)

        expected_median = 3.0
        assert result.loc[1, "a"] == expected_median

    def test_impute_mode(self):
        """Test imputation with mode strategy."""
        df = pd.DataFrame({"a": [1, np.nan, 2, 1, 1, 2]})

        strategy = [{"impute": {"a": "mode"}}]
        result = handle_missing_values(df, strategy)

        assert result.loc[1, "a"] == 1  # Mode is 1

    def test_impute_zero(self):
        """Test imputation with zero strategy."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})

        strategy = [{"impute": {"a": "zero"}}]
        result = handle_missing_values(df, strategy)

        assert result.loc[1, "a"] == 0

    def test_impute_custom_value(self):
        """Test imputation with custom numeric value."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})

        strategy = [{"impute": {"a": 42}}]
        result = handle_missing_values(df, strategy)

        assert result.loc[1, "a"] == 42

    def test_impute_mode_all_missing(self):
        """Test mode imputation when all values are missing."""
        df = pd.DataFrame({"a": [np.nan, np.nan, np.nan]})

        strategy = [{"impute": {"a": "mode"}}]

        with pytest.raises(ValueError, match="Cannot compute mode"):
            handle_missing_values(df, strategy)

    def test_impute_invalid_method(self):
        """Test imputation with invalid method."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})

        strategy = [{"impute": {"a": "invalid_method"}}]

        with pytest.raises(ValueError, match="Unknown imputation method"):
            handle_missing_values(df, strategy)

    def test_impute_nonexistent_column(self):
        """Test imputation on non-existent column."""
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})

        strategy = [{"impute": {"nonexistent": "mean"}}]

        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            handle_missing_values(df, strategy)

    def test_sequential_strategies(self):
        """Test applying multiple strategies sequentially."""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [np.nan, np.nan, np.nan, np.nan, 5],  # 80% missing
                "c": [1, np.nan, 3, np.nan, 5],
                "d": [np.nan, 2, 3, 4, 5],
            }
        )

        strategy = [
            {"drop_columns": 0.7},  # Drop column 'b'
            {"drop_rows": ["d"]},  # Drop row 0 (where 'd' is missing)
            {"impute": {"c": "median"}},  # Impute remaining missing in 'c'
        ]

        result = handle_missing_values(df, strategy)

        # Column 'b' should be dropped
        assert "b" not in result.columns
        # Row 0 should be dropped
        assert 0 not in result.index
        # Column 'c' should have no missing values
        assert not result["c"].isna().any()
        # Verify median imputation (median of [1, 3, 5] after dropping row 0 = 3, but row 1 was NaN so gets median 4.0 from [1, 3, 5])
        assert result.loc[1, "c"] == 4.0  # Median of remaining values [1, 3, 5]

    def test_complex_pipeline(self):
        """Test a complex, realistic missing value pipeline."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5, 6],
                "high_missing": [np.nan] * 5 + [1],  # 83% missing
                "important": [1, np.nan, 3, 4, np.nan, 6],
                "feature1": [1.0, 2.0, np.nan, 4.0, 5.0, np.nan],
                "feature2": [10, 20, 30, np.nan, 50, 60],
            }
        )

        strategy = [
            {"drop_columns": 0.8},  # Drop 'high_missing'
            {"drop_rows": ["important"]},  # Drop rows 1 and 4
            {"impute": {"feature1": "mean", "feature2": "median"}},
        ]

        result = handle_missing_values(df, strategy)

        # Verify column was dropped
        assert "high_missing" not in result.columns
        # Verify rows were dropped
        assert len(result) == 4
        assert result.index.tolist() == [0, 2, 3, 5]
        # Verify no missing values remain
        assert not result.isna().any().any()

    def test_invalid_action_type(self):
        """Test with invalid action type."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"invalid_action": "value"}]

        with pytest.raises(ValueError, match="Unknown action type"):
            handle_missing_values(df, strategy)

    def test_invalid_drop_columns_threshold(self):
        """Test drop_columns with invalid threshold value."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"drop_columns": 1.5}]  # > 1.0

        with pytest.raises(ValueError, match="must be a float between 0 and 1"):
            handle_missing_values(df, strategy)

    def test_invalid_drop_rows_type(self):
        """Test drop_rows with invalid type."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"drop_rows": "not_a_list"}]

        with pytest.raises(ValueError, match="must be a list"):
            handle_missing_values(df, strategy)

    def test_invalid_impute_type(self):
        """Test impute with invalid type."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"impute": "not_a_dict"}]

        with pytest.raises(ValueError, match="must be a dictionary"):
            handle_missing_values(df, strategy)

    def test_invalid_action_format(self):
        """Test with invalid action format (multiple keys)."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        strategy = [{"drop_columns": 0.5, "drop_rows": ["a"]}]

        with pytest.raises(ValueError, match="exactly one key"):
            handle_missing_values(df, strategy)

    def test_original_dataframe_unchanged(self):
        """Test that the original DataFrame is not modified."""
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": [4, 5, 6]})
        df_copy = df.copy()

        strategy = [{"impute": {"a": "mean"}}]
        result = handle_missing_values(df, strategy)

        # Original should be unchanged
        pd.testing.assert_frame_equal(df, df_copy)
        # Result should be different
        assert not result.equals(df)

    def test_empty_strategy_list(self):
        """Test with empty strategy list (should return copy of original)."""
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": [4, 5, 6]})

        strategy = []
        result = handle_missing_values(df, strategy)

        pd.testing.assert_frame_equal(result, df)
        # Verify it's a copy, not the same object
        assert result is not df
