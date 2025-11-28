"""
Data Splitting Functions

This module contains functions for splitting data into training and testing sets.
"""

import pandas as pd
from sklearn.model_selection import train_test_split


def split_data(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 80539,
    stratify: bool = True
):
    """
    Splits data into training and testing sets.

    Args:
        X (pd.DataFrame): Feature matrix
        y (pd.Series): Target variable
        test_size (float): Proportion of data to use for testing (default: 0.2)
        random_state (int): Random seed for reproducibility (default: 80539)
        stratify (bool): Whether to stratify the split based on the target variable (default: True)

    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    # Remove rows with missing target values
    valid_idx = y.notna()
    X_clean = X[valid_idx]
    y_clean = y[valid_idx]

    # Use stratified split if requested
    stratify_param = y_clean if stratify else None

    X_train, X_test, y_train, y_test = train_test_split(
        X_clean,
        y_clean,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_param
    )

    return X_train, X_test, y_train, y_test
