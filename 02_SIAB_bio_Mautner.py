#!/usr/bin/env python3
"""
GENERATION OF BIOGRAPHICAL VARIABLES
Authors: Johanna Eberle, Alexandra Schmucker (original Stata code)
        Converted to Python
Date:   June 2017
SIAB version: 7514 v1
Purpose: Generation of cross sectional data and biographical variables
"""

import pandas as pd
import numpy as np
from datetime import datetime

def generate_bio_variables(siab_data):
    """Main function to generate biographical variables from longitudinal data."""

    # Create observation counters
    siab_data['level1'] = siab_data.groupby(['persnr', 'begepi', 'quelle_gr'])['spell'].rank(method='first') - 1
    siab_data['level2'] = siab_data.groupby(['persnr', 'begepi'])['spell'].rank(method='first') - 1

    # Tag vocational training, interns, and minijobs
    siab_data['azubi'] = (siab_data['erwstat'] == 2).astype(int)
    siab_data['intern'] = (siab_data['erwstat'] == 5).astype(int)
    siab_data['minijob'] = (siab_data['erwstat'] == 3).astype(int)

    # Employment groups (5 categories)
    siab_data['pg5'] = pd.NA
    siab_data.loc[siab_data['erwstat'] == 1, 'pg5'] = 1  # standard
    siab_data.loc[siab_data['erwstat'] == 12, 'pg5'] = 2  # azubis
    siab_data.loc[siab_data['erwstat'] == 14, 'pg5'] = 3  # altersteilzeit
    siab_data.loc[siab_data['erwstat'] == 13, 'pg5'] = 4  # mini-job
    siab_data.loc[siab_data['pg5'].isna(), 'pg5'] = 5  # all other

    # Employment versions (1-3)
    siab_data['emp1_sp'] = ((siab_data['azubi'] != 1) & (siab_data['quelle_gr'] == 1)).astype(int)
    siab_data['emp2_sp'] = ((siab_data['azubi'] != 1) & (siab_data['intern'] != 1) &
                           (siab_data['quelle_gr'] == 1)).astype(int)
    siab_data['emp3_sp'] = ((siab_data['azubi'] != 1) & (siab_data['intern'] != 1) &
                           (siab_data['minijob'] != 1) & (siab_data['quelle_gr'] == 1)).astype(int)

    # First day in employment calculations
    for i in range(1, 4):
        emp_col = f'emp{i}_sp'
        ein_col = f'ein_erw{i}'
        siab_data[ein_col] = pd.NA

        # Group by person and get first employment date
        first_emp = (siab_data[siab_data[emp_col] == 1]
                    .groupby('persnr')['begepi']
                    .transform('min'))
        siab_data.loc[siab_data[emp_col] == 1, ein_col] = first_emp

    # Calculate days in employment
    for i in range(1, 4):
        emp_col = f'emp{i}_sp'
        tage_col = f'tage_erw{i}_kum'

        siab_data[tage_col] = (siab_data[siab_data[emp_col] == 1]
                              .groupby('persnr')
                              .apply(lambda x: (x['endepi'] - x['begepi'] + 1).cumsum()))

    # Parallel jobs processing
    # ... existing code for parallel jobs processing ...

    # First day and days in establishment
    siab_data['ein_bet'] = siab_data.groupby('bnn')['begepi'].transform('min')
    siab_data['tage_bet_kum'] = (siab_data.groupby('bnn')
                                .apply(lambda x: (x['endepi'] - x['begepi'] + 1).cumsum()))

    # Job history processing
    # ... existing code for job history ...

    # Benefit receipt processing (LeH and LHG)
    for source in ['leh', 'lhg']:
        quelle = 2 if source == 'leh' else 3
        siab_data[f'lst_{source}'] = (siab_data['quelle_gr'] == quelle).astype(int)

        # Calculate benefit durations and counts
        # ... existing code for benefit calculations ...

    # Subsidized employment
    siab_data['se_ep'] = ((siab_data['quelle_gr'] == 4) &
                         siab_data['erwstat'].isin([41, 44])).astype(int)

    # Label variables and handle missing values
    # ... existing code for labels and missing values ...

    # Save processed data
    output_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/siab_r_7517_v1_sample_bio_HM.dta"
    siab_data.to_stata(output_path, write_index=False)

    return siab_data

if __name__ == "__main__":
    # Load the data
    data_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/SIAB_sample_UEidenfidied.dta"
    if os.path.exists(data_path):
        siab_data = pd.read_stata(data_path)
        generate_bio_variables(siab_data)
    else:
        print(f"Data file not found: {data_path}")
