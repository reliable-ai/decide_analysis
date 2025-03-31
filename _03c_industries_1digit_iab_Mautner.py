"""
SIAB Preparation

Generate 1-digit industry variable based on 3-digit industries (w93_3_gen)
Mapping based IAB establishment panel
w93_3_gen is already coded time-consistent (see Eberle et al. 2014)

Author(s): Wolfgang Dauth, Johann Eppelsheimer
Converted to Python
"""

import pandas as pd
import numpy as np

def map_industries(df):
    """Map 3-digit industries to 1-digit industries according to IAB panel."""

    # Initialize industry classification column
    df['industry1_estpanel'] = np.nan

    # Group 1: Agriculture, hunting, forestry, fishing, mining, energy
    df.loc[(df['w93_3_gen'].between(11, 50)), 'industry1_estpanel'] = 1
    df.loc[((df['w93_3_gen'].between(101, 145)) |
            (df['w93_3_gen'].between(371, 410)) |
            (df['w93_3_gen'] == 900)), 'industry1_estpanel'] = 1

    # Group 2: Food products, beverages, tobacco
    df.loc[df['w93_3_gen'].between(151, 160), 'industry1_estpanel'] = 2

    # Group 3: Consumer products
    df.loc[((df['w93_3_gen'].between(171, 193)) |
            (df['w93_3_gen'].between(221, 223)) |
            (df['w93_3_gen'].between(361, 366))), 'industry1_estpanel'] = 3

    # Group 4: Industrial goods
    df.loc[((df['w93_3_gen'].between(201, 212)) |
            (df['w93_3_gen'].between(231, 287))), 'industry1_estpanel'] = 4

    # Group 5: Capital and consumer goods
    df.loc[df['w93_3_gen'].between(291, 355), 'industry1_estpanel'] = 5

    # Group 6: Construction and related services
    df.loc[df['w93_3_gen'].between(451, 455), 'industry1_estpanel'] = 6
    df.loc[df['w93_3_gen'].between(551, 555), 'industry1_estpanel'] = 7
    df.loc[df['w93_3_gen'].between(921, 930), 'industry1_estpanel'] = 7

    # Group 7: Trade and maintenance
    df.loc[df['w93_3_gen'].between(501, 527), 'industry1_estpanel'] = 7
    df.loc[df['w93_3_gen'].between(745, 748), 'industry1_estpanel'] = 8

    # Group 8: Business services
    conditions = [
        df['w93_3_gen'].between(601, 634),  # Transport
        df['w93_3_gen'].between(641, 642),  # Communication
        df['w93_3_gen'].between(651, 672),  # Financial
        df['w93_3_gen'].between(701, 703),  # Real estate
        df['w93_3_gen'].between(711, 714),  # Renting
        df['w93_3_gen'].between(721, 726),  # IT
        df['w93_3_gen'].between(731, 744)   # Professional services
    ]
    df.loc[np.any(conditions, axis=0), 'industry1_estpanel'] = 8

    # Group 9: Public and social services
    conditions = [
        df['w93_3_gen'].between(801, 804),  # Education
        df['w93_3_gen'].between(851, 853),  # Health
        df['w93_3_gen'].between(911, 913),  # Organizations
        df['w93_3_gen'].between(751, 753)   # Public admin
    ]
    df.loc[np.any(conditions, axis=0), 'industry1_estpanel'] = 9

    # Create cross-tabulation for verification
    print("\nIndustry Classification Cross-tabulation:")
    print(pd.crosstab(df['w93_3_gen'], df['industry1_estpanel']))

    return df

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
