import pandas as pd
from src.read_data.fix_types import fix_data_types


def test_fix_data_types_converts_dates():
    df = pd.DataFrame(
        {
            "episode_start_date": ["2020-01-01", "2020-02-01"],
            "episode_end_date": ["2020-01-15", "2020-02-15"],
            "other_col": [1, 2],
        }
    )
    result = fix_data_types(df)
    assert pd.api.types.is_datetime64_any_dtype(result["episode_start_date"])
    assert pd.api.types.is_datetime64_any_dtype(result["episode_end_date"])


def test_fix_data_types_handles_missing_columns():
    df = pd.DataFrame({"other_col": [1, 2, 3]})
    result = fix_data_types(df)
    assert "other_col" in result.columns
