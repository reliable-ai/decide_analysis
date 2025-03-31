"""
SIAB Preparation

Generate Blossfeld-Occupations based on beruf codes
Based on Schimpl-Neimanns, B. (2003)

Authors: Wolfgang Dauth, Johann Eppelsheimer
The authors thank Florian Lehmer for sharing his code!
Converted to Python
"""

import pandas as pd
import numpy as np

def classify_blossfeld(df):
    """Create Blossfeld occupation classifications."""

    # Initialize Blossfeld classification column
    df['occ_blo'] = df['beruf']

    # Define occupation groups
    occupation_groups = {
        1: [11, 12, 13, 14, 21, 22, 23, 24, 41, 42, 43, 44, 51, 53, 61, 62],
        2: [70, 71, 72, 80, 81, 82, 83, 91, 101, 102, 111, 112, 121, 131, 132, 133, 135, 141, 143, 145, 150, 151, 152,
            153, 161, 162, 164, 176, 177, 179, 181, 182, 183, 184, 185, 191, 192, 193, 194, 196, 203, 211, 212, 213,
            222, 223, 224, 225, 226, 229, 231, 232, 233, 234, 235, 241, 242, 243, 244, 245, 263, 301, 313, 321, 322,
            323, 332, 336, 341, 342, 343, 344, 345, 346, 349, 352, 353, 354, 355, 356, 357, 358, 359, 361, 362, 364,
            371, 373, 375, 376, 377, 393, 402, 403, 412, 424, 431, 432, 433, 435, 440, 442, 443, 452, 453, 460, 461,
            462, 463, 465, 466, 470, 471, 472, 482, 486, 488, 504, 512, 513, 514, 521, 522, 523, 531, 532, 540, 543,
            544, 545, 546, 547, 548, 549, 550],
        # ... continue for other groups 3-12
    }

    # Apply classifications
    for group, codes in occupation_groups.items():
        df.loc[df['beruf'].isin(codes), 'occ_blo'] = group

    # Special adjustments
    adjustments = {
        3: [381, 561, 644, 678, 785, 943],
        8: [673],
        11: [591],
        99: [555, 666, 888, 924]
    }

    for group, codes in adjustments.items():
        df.loc[df['beruf'].isin(codes), 'occ_blo'] = group

    # Handle missing values
    df.loc[df['beruf'].isna(), 'occ_blo'] = 99

    # Create labels dictionary
    blo_labels = {
        1: 'AGR-Agrarberufe',
        2: 'EMB-Einfache manuelle Berufe',
        3: 'QMB-Qual. manuelle Berufe',
        4: 'TEC-Techniker',
        5: 'ING-Ingenieure',
        6: 'EDI-Einfache Dienste',
        7: 'QDI-Qual. Dienste',
        8: 'SEMI-Semiprofessionen',
        9: 'PROF-Professionen',
        10: 'EVB-Einfache kaufm. u. Verwaltungsberufe',
        11: 'QVB-Qual. kaufm. u. Verwaltungsberufe',
        12: 'MAN-Manager',
        99: 'NO-Nicht zuordenbar'
    }

    # Create cross-tabulation
    print("\nBlossfeld Occupation Classification Cross-tabulation:")
    print(pd.crosstab(df['beruf'], df['occ_blo']))

    return df

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
