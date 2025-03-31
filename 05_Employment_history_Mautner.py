"""
SIAB Preparation
Employment History Processing

Creates employment history variables for individuals in the dataset.
Processes various aspects of employment including durations, types, and characteristics.

Author: Hannah Mautner
Converted to Python
"""

import pandas as pd
import numpy as np

def process_employment_history(df):
    """Process employment history for all individuals."""

    # Initialize tracking variables
    df['lhgspell'] = df['quelle_gr'] == 3
    df['behspell'] = df['quelle_gr'] == 1
    df['lehspell'] = df['quelle_gr'] == 2
    df['asuspell'] = df['quelle_gr'] == 5
    df['mthspell'] = df['quelle_gr'] == 4

    # Process previous status (6 weeks prior)
    df = process_previous_status(df)

    # Process employment counts and durations
    df = process_employment_counts(df)

    # Process industry information
    df = process_industry_info(df)

    # Process last job information
    df = process_last_job(df)

    # Process various employment types duration
    df = process_employment_types(df)

    # Process job seeking history
    df = process_job_seeking(df)

    # Process benefit history
    df = process_benefits(df)

    # Process ALMP history
    df = process_almp_history(df)

    # Process biographical variables
    df = process_biographical(df)

    return df

def process_previous_status(df):
    """Process status before unemployment episode."""
    # Select relevant date
    df['status_beg_date'] = df.groupby('persnr')['begepi'].transform('max')

    # Calculate time since previous spell
    df['t_since_spell'] = df['beg_relevant_ue_date'] - df['endepi'] + 1

    # Create status indicators for 6 weeks prior
    status_window = df['t_since_spell'] <= 42
    for status in ['employed', 'receipt_leh', 'receipt_lhg', 'se', 'ASU_notue_seeking']:
        df[f'{status}_before'] = df.groupby('persnr')[status].transform('max').where(status_window, 0)

    return df

def process_employment_counts(df):
    """Process counts and durations of different employment types."""
    # Filter to employment spells
    emp_spells = df[df['behspell']].copy()

    # Count unique jobs
    df['emp_total'] = emp_spells.groupby('persnr')['ein_job'].nunique()

    # Calculate employment durations
    duration_cols = ['emp1_total_dur', 'emp2_total_dur', 'emp3_total_dur']
    for i, col in enumerate(duration_cols, 1):
        df[col] = emp_spells.groupby('persnr')[f'tage_erw{i}_kum'].transform('max')

    return df

# ... Additional function implementations for other processing steps ...

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
