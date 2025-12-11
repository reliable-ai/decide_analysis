"""
Model Setup Functions

This module contains functions for preparing data for machine learning models,
including feature selection and target variable extraction.
"""

from typing import Literal
import pandas as pd


def select_features(df: pd.DataFrame, strategy: Literal["default"] = "default") -> pd.DataFrame:
    """
    Selects feature columns from the dataframe for modeling.

    Excludes the target variable (ltue) and non-feature columns like IDs,
    dates, and other metadata that shouldn't be used for prediction.

    Args:
        df (pd.DataFrame): Input dataframe with all variables

    Returns:
        pd.DataFrame: Dataframe containing only feature columns
    """
    # Columns to exclude from features
    exclude_cols = [
        "ltue",
        "person_id",
        "nrEntry",
        "year",

        # Normally excluded earlier?
        "ue_duration",
        "episode_start_date",
        "episode_end_date",
    ]

    for col in exclude_cols:
        if col not in df.columns:
            print(
                f"Warning: Column to exclude '{col}' not found in dataframe, "
                "are the assumptions of the data met?"
            )

    # Get all columns that are not in the exclude list
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # Return only feature columns
    X = df[feature_cols].copy()

    return X


def select_target(df: pd.DataFrame) -> pd.Series:
    """
    Extracts the target variable (ltue) from the dataframe.

    The target variable indicates long-term unemployment:
    - 1: Long-term unemployment (>= 365 days)
    - 0: Short-term unemployment (< 365 days)

    Args:
        df (pd.DataFrame): Input dataframe containing the target variable

    Returns:
        pd.Series: Target variable series
    """
    if "ltue" not in df.columns:
        raise ValueError("Target variable 'ltue' not found in dataframe")

    y = df["ltue"].copy()

    return y
