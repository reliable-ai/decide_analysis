"""
Model Setup Functions

This module contains functions for preparing data for machine learning models,
including feature selection and target variable extraction.
"""

import pandas as pd


def select_features(
    df: pd.DataFrame, features: list[str] | None = None, additional_exclude: list[str] | None = None
) -> pd.DataFrame:
    """
    Selects feature columns from the dataframe for modeling.

    Excludes the target variable (ltue) and non-feature columns like IDs,
    dates, and other metadata that shouldn't be used for prediction.

    Args:
        df (pd.DataFrame): Input dataframe with all variables
        features (list[str] | None): Optional list of feature column names to
            select. If provided, only these features will be returned. If None,
            uses default exclusion logic to select features.
        additional_exclude (list[str] | None): Optional list of additional column
            names to exclude from features.

    Returns:
        pd.DataFrame: Dataframe containing only feature columns
    """
    # exclude certain columns
    exclude_cols = [
        "ltue",
        "person_id",
        "nrEntry",
        "year",
        # normally excluded earlier in the data cleaning process?
        "ue_duration",
        "episode_start_date",
        "episode_end_date",
    ]

    if additional_exclude is not None:
        exclude_cols.extend(additional_exclude)

    if features is not None:
        # if specific features are requested, use only those
        missing_features = [col for col in features if col not in df.columns]
        if missing_features:
            raise ValueError(
                f"Requested features not found in dataframe: {missing_features}"
            )

        # validate that target/excluded columns aren't accidentally included
        invalid_features = [col for col in features if col in exclude_cols]
        if invalid_features:
            raise ValueError(
                f"Cannot include the following columns as \
                    features: {invalid_features}. \
                    These columns should not be used for modeling."
            )

        return df[features].copy()


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
