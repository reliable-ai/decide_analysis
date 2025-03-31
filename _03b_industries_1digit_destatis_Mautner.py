"""
SIAB Preparation

Generate 1-digit industry variable based on classification w08_gen_gr
Mapping based on Statistisches Bundesamt (2002)

Author(s): Wolfgang Dauth, Johann Eppelsheimer
Converted to Python
"""

import pandas as pd
import numpy as np

def process_industries(df):
    """Process industry classifications."""

    # Create new industry classification
    df['indust'] = np.nan

    # Map values 1:1 from w08_gen_gr to indust
    for i in range(1, 15):  # Values 1-14
        df.loc[df['w08_gen_gr'] == i, 'indust'] = i

    # Copy the label mapping from w08_gen_gr_de to new INDUST label
    # Note: In Python/Pandas, we typically handle categories using category dtype
    # or keep a separate mapping dictionary for labels

    # Create tabulation of results
    cross_tab = pd.crosstab(df['w08'], df['indust'], margins=True)
    print("\nIndustry Classification Cross-tabulation:")
    print(cross_tab)

    return df

if __name__ == "__main__":
    # This code will only run if the script is run directly
    # When imported as a module in the master script, this section is skipped
    print("This script should be run as part of the master SIAB processing pipeline")
