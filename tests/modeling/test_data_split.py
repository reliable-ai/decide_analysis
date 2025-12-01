import pytest
import pandas as pd
import numpy as np
from modeling.data_split import split_data


def test_split_data_basic():
    X = pd.DataFrame({"feature1": range(20), "feature2": range(20, 40)})
    y = pd.Series([0, 1] * 10)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2, random_state=42)
    assert len(X_train) + len(X_test) == 20
    assert len(y_train) == len(X_train)


def test_split_data_removes_missing_targets():
    X = pd.DataFrame({"feature1": range(10)})
    y = pd.Series([0, 1, 0, 1, np.nan, 0, 1, 0, 1, 0])
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.3, random_state=42)
    assert len(X_train) + len(X_test) == 9
