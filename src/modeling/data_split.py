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
    stratify: bool = True,
    chronological: bool = False,
):
    """
    Splits data into training and testing sets.

    Args:
        X (pd.DataFrame): Feature matrix
        y (pd.Series): Target variable
        test_size (float): Proportion of data to use for testing (default: 0.2)
        random_state (int): Random seed for reproducibility (default: 80539)
        stratify (bool): Whether to stratify the split based on the target
            variable. Only used when chronological=False (default: True)
        chronological (bool): Whether to split chronologically based on
            'episode_end_date' column. When True, all test observations will
            come after training observations in time. Stratification is disabled
            when chronological=True (default: False)

    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    
    # remove rows with missing target values
    valid_idx = y.notna()
    X_clean = X[valid_idx]
    y_clean = y[valid_idx]
    
    # check that both chronological and stratify are not True at the same time
    if chronological and stratify:
        raise ValueError("Cannot use both chronological and stratified splits \
            at the same time.")
    
    if chronological:
        # chronological split needs date column
        if 'episode_end_date' not in X_clean.columns:
            raise ValueError("'episode_end_date' column not found in X. \
                Required for chronological split.")
        
        # remove rows with missing dates
        date_valid_idx = X_clean['episode_end_date'].notna()
        X_clean = X_clean[date_valid_idx]
        y_clean = y_clean[date_valid_idx]
        
        # sort by date to ensure chronological order
        sort_idx = X_clean['episode_end_date'].argsort()
        X_clean = X_clean.iloc[sort_idx]
        y_clean = y_clean.iloc[sort_idx]
        
        # calculate split point
        n_samples = len(X_clean)
        n_test = int(n_samples * test_size)
        n_train = n_samples - n_test
        
        # split chronologically: first n_train for training,
        # last n_test for testing
        X_train = X_clean.iloc[:n_train]
        X_test = X_clean.iloc[n_train:]
        y_train = y_clean.iloc[:n_train]
        y_test = y_clean.iloc[n_train:]
        

    else:
        # use stratified split if requested (only for non-chronological splits)
        stratify_param = y_clean if stratify else None

        X_train, X_test, y_train, y_test = train_test_split(
            X_clean,
            y_clean,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify_param,
        )

    return X_train, X_test, y_train, y_test
