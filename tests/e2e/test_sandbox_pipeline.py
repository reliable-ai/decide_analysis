import pandas as pd

from src.read_data.read_data import read_data
from src.read_data.translate_names import translate_to_english
from src.read_data.fix_types import fix_data_types
from src.data_cleaning.feature_engineering import (
    identify_unemployment_episodes,
    generate_biographical_variables,
    index_unemployment_entries,
    generate_employment_history,
)
from src.data_cleaning.transform import reshape_data_for_ml
from src.modeling.setup import select_features, select_target


def _run_sandbox_pipeline(n_rows: int = 5000) -> tuple[pd.DataFrame, pd.Series]:
    df = read_data(n_rows)
    df = translate_to_english(df)
    df = fix_data_types(df)
    df = identify_unemployment_episodes(df)
    df = generate_biographical_variables(df)
    df = index_unemployment_entries(df)
    df = generate_employment_history(df, 1)
    df = reshape_data_for_ml(df)

    # Match the sandbox NA handling workaround
    df = df.replace(99999, pd.NA)
    df = df.fillna(0)

    X = select_features(df)
    y = select_target(df)
    return X, y


def test_sandbox_pipeline(snapshot):
    X, y = _run_sandbox_pipeline()

    # Snapshot the ordered list of column names
    assert list(X.columns) == snapshot(name="X: Columns")

    # Snapshot the shapes of features and target for stability
    assert X.shape == snapshot(name="X: Shape")
    assert y.shape == snapshot(name="y: Shape")
