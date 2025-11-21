# imports
import pandas as pd

def fix_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts date columns to datetime objects for date arithmetic operations.
    
    Args:
        df (pd.DataFrame): Dataset with date columns that may be strings.
    
    Returns:
        pd.DataFrame: Dataset with date columns converted to datetime objects.
    """
    df = df.copy()
    
    # convert date columns to datetime for date arithmetic
    date_columns = ['episode_start_date', 'episode_end_date',
                    'observation_start_date', 'observation_end_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    return df