import pandas as pd
import numpy as np

def replace_missing_value_placeholder(df: pd.DataFrame, placeholder: int = 99999) -> pd.DataFrame:
    """
    Replace all instances of a placeholder value (e.g., 99999) with NaN.
    
    Args:
        df: Input DataFrame
        placeholder: The placeholder value to replace (default: 99999)
        
    Returns:
        DataFrame with placeholder values replaced by NaN
    """
    
    return df.replace(placeholder, np.nan)

def handle_missing_values(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """
    Handle missing values in the DataFrame by applying specific rules.
    
    Args:
        df: Input DataFrame
        strategy: Method to handle missing values ('drop', 'fill_mean', 'fill_median')
    """
    
    # drop columns that have NaNs
    if strategy == "drop_columns":
        df = df.dropna(axis=1)
    # drop rows that have NaNs
    elif strategy == "drop_rows":
        df = df.dropna(axis=0)
    # fill NaNs with zeros
    elif strategy == "zero":
        df = df.fillna(0)
    # fill NaNs with column mean
    elif strategy == "mean":
        df = df.fillna(df.mean())
    # fill NaNs with column median
    elif strategy == "median":
        df = df.fillna(df.median())
    else:
        raise ValueError(f"Unknown method: {strategy}")

    return df