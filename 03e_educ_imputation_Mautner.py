"""
SIAB Preparation

Imputation of the education variable 'ausbildung'
Based on Fitzenberger, Osikominu & Voelter (2008) (Imputation Procedure 1)

Author(s): Wolfgang Dauth, Johann Eppelsheimer
Converted to Python
"""

import pandas as pd
import numpy as np

def impute_education(df):
    """Impute education values following Fitzenberger et al. (2008)."""

    # Generate new education variable
    df['ausbildung_imp'] = df['ausbildung'].copy()

    # Translate ASU, XASU and MTH Ausbildung into BeH Ausbildung
    translations = {
        5: 11,    # FH --> FH
        6: 12,    # Uni --> Uni
        3: 2,     # Berufsfachschule --> betr./außerbetr. Ausbildung
        4: 2,     # Fachschule --> betr./außerbetr. Ausbildung
        7: 1,     # nicht anerkannt ausl. Ausb. --> ohne Ausbildung
        8: 1      # nicht anerkannt ausl. Uni --> ohne Ausbildung
    }

    df['ausbildung_imp'].replace(translations, inplace=True)

    # Replace missing values with 0
    df['ausbildung_imp'].fillna(0, inplace=True)

    # Take highest value for parallel spells
    df['ausbildung_max'] = df.groupby(['persnr', 'begepi'])['ausbildung_imp'].transform('max')
    df.loc[df['ausbildung_imp'] < df['ausbildung_max'], 'ausbildung_imp'] = df['ausbildung_max']
    df.drop('ausbildung_max', axis=1, inplace=True)

    # Step 1: No educational degree if age < 18
    df.loc[df['age'] < 18, 'ausbildung_imp'] = 1

    # Step 2: Forward extrapolation
    df.sort_values(['persnr', 'begepi', 'quelle'], inplace=True)
    df['prev_ausbildung'] = df.groupby('persnr')['ausbildung_imp'].shift(1)
    df.loc[(df['prev_ausbildung'] > df['ausbildung_imp']) & (df['prev_ausbildung'].notna()),
           'ausbildung_imp'] = df['prev_ausbildung']
    df.drop('prev_ausbildung', axis=1, inplace=True)

    # Step 3: Backward extrapolation
    df.sort_values(['persnr', 'begepi', 'quelle'], ascending=[True, False, False], inplace=True)

    # Apply backward extrapolation rules with age limits
    for prev_val, new_val, age_limit, extra_cond in [
        (1, 1, 0, None),
        (2, 2, 20, ~df['erwstat'].isin([102, 121, 122, 141])),
        (11, 11, 27, None),
        (12, 12, 29, None)
    ]:
        mask = (
            (df.groupby('persnr')['ausbildung_imp'].shift(-1) == prev_val) &
            (df['ausbildung_imp'] == 0)
        )
        if age_limit > 0:
            mask &= (df['age'] >= age_limit)
        if extra_cond is not None:
            mask &= extra_cond
        df.loc[mask, 'ausbildung_imp'] = new_val

    # Set remaining zeros to NaN
    df['ausbildung_imp'].replace(0, np.nan, inplace=True)

    # Generate more general education variable
    df['educ'] = pd.NA
    df.loc[df['ausbildung_imp'].isin([11, 12]), 'educ'] = 3  # university degrees
    df.loc[df['ausbildung_imp'] == 2, 'educ'] = 2            # vocational training
    df.loc[df['ausbildung_imp'] == 1, 'educ'] = 1            # no training

    # Restore original sort order
    df.sort_values(['persnr', 'begepi', 'quelle'], inplace=True)

    # Print verification tables
    print("\nEducation Classification Cross-tabulation:")
    print(pd.crosstab(df['ausbildung'], df['ausbildung_imp'], margins=True))

    return df

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
