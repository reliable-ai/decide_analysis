"""
SIAB Preparation

Index entries into unemployment
Process all entries into unemployment per individual

Author: Hannah Mautner
Converted to Python
"""

import pandas as pd
import numpy as np

def process_entries(df):
    """Index unemployment entries for each person.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with indexed unemployment entries
    """
    # Create temporary dataframe with only unemployment entries 2010-2017
    entries_df = df[
        (df['beg_ue'] == 1) &
        (df['year'].between(2010, 2017))
    ].copy()

    # Generate index for unemployment entries
    entries_df['nrEntry'] = entries_df.groupby('persnr').cumcount() + 1

    # Keep only necessary columns for merging back
    entries_df = entries_df[['persnr', 'spell', 'nrEntry']]

    # Merge back to original dataframe
    df = df.merge(entries_df, on=['persnr', 'spell'], how='left')

    # Verify results
    print("\nUnemployment Entry Statistics:")
    print(df.groupby('year')['nrEntry'].describe())

    return df

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
