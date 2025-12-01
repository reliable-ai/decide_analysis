import pytest
import pandas as pd
from modeling.setup import select_features, select_target


def test_select_features_excludes_target():
    df = pd.DataFrame({
        "ltue": [0, 1, 0],
        "person_id": [1, 2, 3],
        "feature1": [10, 20, 30],
        "feature2": [40, 50, 60]
    })
    X = select_features(df)
    assert "ltue" not in X.columns
    assert "person_id" not in X.columns
    assert "feature1" in X.columns


def test_select_features_keeps_predictors():
    df = pd.DataFrame({
        "ltue": [0, 1],
        "age": [25, 30],
        "female": [1, 0]
    })
    X = select_features(df)
    assert len(X.columns) == 2


def test_select_target_extracts_ltue():
    df = pd.DataFrame({"ltue": [0, 1, 0, 1], "other_col": [1, 2, 3, 4]})
    y = select_target(df)
    assert y.name == "ltue"
    assert len(y) == 4


def test_select_target_raises_on_missing():
    df = pd.DataFrame({"other_col": [1, 2, 3]})
    with pytest.raises(ValueError):
        select_target(df)
