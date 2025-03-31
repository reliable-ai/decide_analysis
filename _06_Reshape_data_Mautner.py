"""
SIAB Preparation

Reshape data for machine learning models.
Process and clean variables, handling missing values and creating final dataset structure.

Author: Hannah Mautner
Converted to Python
"""

import pandas as pd
import numpy as np

def process_reshape(df):
    """Reshape and prepare data for machine learning models.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Reshaped and cleaned data frame ready for ML
    """
    # Handle missings for deutsch
    df['deutsch'] = df['deutsch'].replace({99999: -1, '.a': -2})
    df['maxdeutsch'] = df.groupby('persnr')['deutsch'].transform('max')

    # Handle missings for ausbildung_imp
    df['ausbildung_imp'] = df['ausbildung_imp'].replace({99999: -1})
    df['maxausbildung_imp'] = df.groupby('persnr')['ausbildung_imp'].transform('max')

    # Handle missings for schule
    df['schule'] = df['schule'].replace({'.n': -1, '.z': -2})
    df['maxschule'] = df.groupby('persnr')['schule'].transform('max')

    # Handle missings for niveau
    df['niveau'] = df['niveau'].replace({'.n': -1, '.z': -2})
    df['maxniveau'] = df.groupby('persnr')['niveau'].transform('max')

    # Create Bundesland mapping
    def map_to_bula(x):
        if pd.isna(x):
            return np.nan
        x = int(x)
        for i in range(1, 17):
            if x < (i+1)*1000 and x >= i*1000:
                return i
        return np.nan

    df['bula'] = df['ao_reg'].apply(map_to_bula)

    # Get most recent Bundesland
    df['maxbula'] = df.sort_values('begepi').groupby('persnr')['bula'].transform('last')

    # Handle pendler (commuter) information
    df['pendler'] = df['pendler'].replace({'.n': -1, '.z': -2})
    df['maxpendler'] = df.sort_values('begepi').groupby('persnr')['pendler'].transform('last')

    # Handle industry sector information
    df['w08_gen_gr'] = df['w08_gen_gr'].replace({'.n': -1, '.z': -2})
    df['lastw08_gen_gr'] = df.sort_values('begepi').groupby('persnr')['w08_gen_gr'].transform('last')

    # Keep only unemployment entry spells
    df = df[df['relevant_ue'] == 1].copy()

    # Create variable groups for organization
    variable_groups = {
        'response': ['ltue'],
        'spell_original': ['persnr', 'year', 'quelle_gr', 'begepi', 'endepi', 'alo_dau'],
        'spell_generated': ['ue_pop', 'nrEntry', 'beg_ue', 'ue_duration'],
        'status_before': ['employed_before', 'receipt_leh_before', 'receipt_lhg_before',
                         'se_before', 'ASU_notue_seeking_before', 'ASU_other_before', 'break_before'],
        # ... additional variable groups as needed
    }

    # Create final dataset with selected columns in proper order
    columns_to_keep = []
    for group in variable_groups.values():
        columns_to_keep.extend(group)

    # Add the newly created max/last variables
    additional_cols = ['maxdeutsch', 'maxausbildung_imp', 'maxbula', 'maxniveau',
                      'maxschule', 'maxpendler', 'lastw08_gen_gr']
    columns_to_keep.extend(additional_cols)

    # Select final columns and add labels
    df = df[columns_to_keep].copy()

    # Add variable labels (as dictionary for documentation)
    variable_labels = {
        'maxdeutsch': 'most recent nationality, neg.value=mis',
        'maxausbildung_imp': 'most recent education, neg.value=mis',
        'maxschule': 'most recent school education, neg.value=mis',
        'maxniveau': 'most recent niveau of job, neg.value=mis',
        'maxbula': 'most recent Bundesland',
        'maxpendler': 'most recent commute',
        'lastw08_gen_gr': 'most recent sector'
        # ... additional labels as needed
    }

    return df

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
