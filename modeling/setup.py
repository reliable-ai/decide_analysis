"""
Model Setup Functions

This module contains functions for preparing data for machine learning models,
including feature selection and target variable extraction.
"""

import pandas as pd


def select_features(df: pd.DataFrame) -> pd.DataFrame:
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
        # Target variable
        'ltue',
        # IDs and identifiers
        'person_id',
        'establishment_id',
        'spell_count',
        # Dates
        'episode_start_date',
        'episode_end_date',
        'observation_start_date',
        'observation_end_date',
        'beg_ue_date',
        'end_ue_date',
        'next_employed_date',
        'first_day_estab',
        'first_day_job',
        # Other metadata that shouldn't be used for prediction
        'spell_source',
        'beg_ue',
        'end_ue',
        'relevant_ue',
        'ue_pop',
    ]

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
    if 'ltue' not in df.columns:
        raise ValueError("Target variable 'ltue' not found in dataframe")

    y = df['ltue'].copy()

    return y
