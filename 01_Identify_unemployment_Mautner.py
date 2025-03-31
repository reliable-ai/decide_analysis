#!/usr/bin/env python3
"""
IDENTIFICATION OF (LONG-TERM) UNEMPLOYMENT EPISODES

Author: Hannah Mautner (original Stata code)
       Converted to Python

Goals:
    - Identify population of job seekers/unemployed
    - Divide into long-term and short term job seeking/unemployment episodes

Approach:
    1. Identify spells that indicate seeking while seeking being unemployment
       - also, identify spells that do not pause unemployment episodes:
         - illness up to 6 weeks
         - certain ALMP measures
    2. Identify separate unemployment episodes
       2.1 Find begin of unemployment (ASU spell)
       2.2 Find end of unemployment (ASU spell)
    3. Calculate the length of unemployment
    4. Identify population of short-term and long-term unemployed/job seekers in 2010-2013
       4.1 Find exits into employment
       4.2 Find LTUE and STUE population for supervised learning models
         - Note: Unemployment episodes that start in 2014 cannot be considered
    5. Data preparations for further steps
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# The script assumes that siab_data is available in the global environment
# from the master script (0_Master_Mautner.py)

def process_unemployment(df):
    """Process unemployment episodes in SIAB data.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with added unemployment episode information
    """
    # YEAR OF OBSERVATION AND AGE
    df['year'] = pd.DatetimeIndex(df['begepi']).year
    df['age'] = df['year'] - df['gebjahr']

    # Keep only (X)ASU and MTH spells for identification of unemployment
    # In Stata this is done with a preserve/restore block
    # In Python, we'll use a separate DataFrame
    ue_data = df[df['quelle_gr'].isin([4, 5])].copy()

    # 1. Identify spells when seeking for employment while being unemployed
    # Identify job seeking while being unemployed (seeking1)
    ue_data['seeking1'] = ((ue_data['quelle_gr'] == 5) & (ue_data['erwstat'] == 21)).astype(int)

    # Identify participation in qualified measures
    ue_data['quelle2'] = -ue_data['quelle_gr']  # Reorder quelle_gr for indexing

    # Generate nrM similar to Stata's bysort persnr begepi(quelle2): gen nrM = _n if...
    # First sort as needed
    ue_data = ue_data.sort_values(['persnr', 'begepi', 'quelle2'])

    # Create a grouping key for the bysort operation
    ue_data['group_key'] = ue_data['persnr'].astype(str) + '_' + ue_data['begepi'].astype(str)

    # Create sequence number within each group
    ue_data['nrM'] = ue_data.groupby('group_key').cumcount() + 1

    # Apply the condition
    mask = (ue_data['quelle_gr'] == 4) & (ue_data['erwstat'] == 41)
    ue_data.loc[~mask, 'nrM'] = np.nan

    # Generate almp variable
    ue_data['almp'] = np.nan
    ue_data.loc[ue_data['nrM'] > 0, 'almp'] = 1

    # Propagate almp values from previous row if in same person and begepi
    ue_data = ue_data.sort_values(['persnr', 'spell'])
    for i in range(1, len(ue_data)):
        if (ue_data.iloc[i]['persnr'] == ue_data.iloc[i-1]['persnr'] and
            ue_data.iloc[i]['begepi'] == ue_data.iloc[i-1]['begepi'] and
            pd.isna(ue_data.iloc[i]['almp'])):
            ue_data.iloc[i, ue_data.columns.get_loc('almp')] = ue_data.iloc[i-1]['almp']

    # Drop auxiliary variables, establish standard sorting
    ue_data = ue_data.drop(['quelle2', 'nrM', 'almp', 'group_key'], axis=1)
    ue_data = ue_data.sort_values(['persnr', 'spell'])

    # Keep only (X)ASU spells that are relevant for determining LTE
    ue_data = ue_data[ue_data['seeking1'] == 1].copy()

    # Calculate days in between ASU job seeking while unemployed spells
    ue_data = ue_data.sort_values(['persnr', 'seeking1', 'begepi'])
    ue_data['t_since_seeking'] = ue_data.groupby(['persnr', 'seeking1'])['begepi'].diff()
    ue_data.loc[ue_data['seeking1'] != 1, 't_since_seeking'] = np.nan

    # Calculate time since last ASU spell
    ue_data = ue_data.sort_values(['persnr', 'spell'])
    ue_data['t_since_asu'] = ue_data.groupby('persnr')['begepi'].diff()

    # Tag spells that are part of a continuous job seeking episode
    ue_data['continuous'] = np.where(ue_data['t_since_asu'] <= 42, 1, np.nan)

    # 2.1 Begin of unemployment
    ue_data = ue_data.sort_values(['persnr', 'spell'])
    ue_data['beg_ue'] = np.where(ue_data['continuous'] != 1, 1, np.nan)

    ue_data = ue_data.sort_values(['persnr', 'seeking1', 'spell'])
    ue_data['beg_ue_date'] = np.where(ue_data['beg_ue'] == 1, ue_data['begepi'], pd.NaT)

    # Copy date to all subsequent ASU spells in the same episode
    ue_data = ue_data.sort_values(['persnr', 'spell'])
    for i in range(1, len(ue_data)):
        if (pd.isna(ue_data.iloc[i]['beg_ue_date']) and
            ue_data.iloc[i]['continuous'] == 1 and
            ue_data.iloc[i]['persnr'] == ue_data.iloc[i-1]['persnr']):
            ue_data.iloc[i, ue_data.columns.get_loc('beg_ue_date')] = ue_data.iloc[i-1]['beg_ue_date']

    # 2.2 End of unemployment
    ue_data = ue_data.sort_values(['persnr', 'spell'])
    ue_data['end_ue'] = np.nan

    # End is defined as the spell previous to a beginning
    for i in range(0, len(ue_data)-1):
        if (ue_data.iloc[i+1]['beg_ue'] == 1 and
            ue_data.iloc[i]['persnr'] == ue_data.iloc[i+1]['persnr']):
            ue_data.iloc[i, ue_data.columns.get_loc('end_ue')] = 1

    # Correction for last end of unemployment
    ue_data['nrASU'] = ue_data.groupby('persnr').cumcount() + 1
    ue_data['NrASU'] = ue_data.groupby('persnr')['nrASU'].transform('max')
    ue_data.loc[ue_data['nrASU'] == ue_data['NrASU'], 'end_ue'] = 1

    # Date of end of unemployment
    ue_data['end_ue_date_help'] = np.where(ue_data['end_ue'] == 1, ue_data['endepi'], pd.NaT)
    ue_data['end_ue_date'] = ue_data.groupby(['persnr', 'beg_ue_date'])['end_ue_date_help'].transform('max')

    # Drop auxiliary variables
    ue_data = ue_data.drop(['nrASU', 'NrASU', 'end_ue_date_help'], axis=1)
    ue_data = ue_data.sort_values(['persnr', 'spell'])

    # 3 Calculate the length/duration of unemployment
    # Duration: Calculate for last ASU spell of continuous unemployment
    ue_data['duration_help'] = np.where(ue_data['end_ue'] == 1,
                                      (ue_data['endepi'] - ue_data['beg_ue_date']).dt.days,
                                      np.nan)

    # Copy UE duration to all spells of an UE episode
    ue_data['ue_duration'] = ue_data.groupby(['persnr', 'beg_ue_date'])['duration_help'].transform('max')

    # Drop auxiliary variables
    ue_data = ue_data.drop(['duration_help'], axis=1)
    ue_data = ue_data.sort_values(['persnr', 'spell'])

    # Keep only necessary columns before merging back
    ue_cols = ['persnr', 'spell', 'seeking1', 't_since_seeking', 't_since_asu',
              'beg_ue', 'end_ue', 'beg_ue_date', 'end_ue_date', 'ue_duration']
    ue_data = ue_data[ue_cols]

    # Merge with the original data (similar to Stata's restore)
    merged_data = pd.merge(df, ue_data, on=['persnr', 'spell'], how='left')

    # 4 Identify STUE and LTUE populations
    # 4.1 Find exits into employment

    # Preserve subset of data for finding exits into employment
    beh_xasu = merged_data[merged_data['quelle_gr'].isin([1, 5])].copy()
    beh_xasu = beh_xasu[(~beh_xasu['quelle_gr'].isin([5])) | (beh_xasu['end_ue'] == 1)]

    # Recode quelle_gr
    beh_xasu['quelle_gr_help'] = np.where(beh_xasu['quelle_gr'] == 5, 1, 2)

    # Generate nrASU
    beh_xasu = beh_xasu.sort_values(['persnr', 'begepi', 'quelle_gr_help', 'end_ue'])
    beh_xasu['group_key'] = (beh_xasu['persnr'].astype(str) + '_' +
                           beh_xasu['begepi'].astype(str) + '_' +
                           beh_xasu['quelle_gr_help'].astype(str))
    beh_xasu['nrASU'] = beh_xasu.groupby('group_key').cumcount() + 1
    beh_xasu = beh_xasu[~((beh_xasu['nrASU'] > 1) & (beh_xasu['quelle_gr_help'] == 1))]

    # Date of next employment
    beh_xasu['next_employed_date'] = np.where(
        (beh_xasu['quelle_gr'] == 1) & (beh_xasu['erwstat'] == 1),
        beh_xasu['begepi'],
        pd.NaT
    )

    # Forward fill next_employed_date within each person
    beh_xasu = beh_xasu.sort_values(['persnr', 'spell', 'quelle_gr'])
    for i in range(len(beh_xasu)-2, -1, -1):
        if (pd.isna(beh_xasu.iloc[i]['next_employed_date']) and
            beh_xasu.iloc[i]['persnr'] == beh_xasu.iloc[i+1]['persnr'] and
            beh_xasu.iloc[i+1]['next_employed_date'] != beh_xasu.iloc[i+1]['begepi']):
            beh_xasu.iloc[i, beh_xasu.columns.get_loc('next_employed_date')] = beh_xasu.iloc[i+1]['next_employed_date']

    # Time till next employment
    beh_xasu['t_till_emp'] = np.where(
        beh_xasu['end_ue'] == 1,
        (beh_xasu['next_employed_date'] - beh_xasu['endepi']).dt.days - 1,
        np.nan
    )

    # Keep only end_ue spells and necessary columns
    beh_xasu = beh_xasu[beh_xasu['end_ue'] == 1]
    beh_xasu = beh_xasu[['persnr', 'spell', 'next_employed_date', 't_till_emp']]

    # Merge back with the main data
    merged_data = pd.merge(merged_data, beh_xasu, on=['persnr', 'spell'], how='left')

    # Rename columns for subsequent processing
    merged_data = merged_data.rename(columns={
        'next_employed_date': 'next_employed_date_help',
        't_till_emp': 't_till_emp_help'
    })

    # Copy next_employed_date and t_till_emp to all spells of same job seeking episode
    merged_data['next_employed_date'] = merged_data.groupby(['persnr', 'beg_ue_date'])['next_employed_date_help'].transform('max')
    merged_data['t_till_emp'] = merged_data.groupby(['persnr', 'beg_ue_date'])['t_till_emp_help'].transform('max')

    # Generate auxiliary variable to determine exit into employment
    merged_data['exit_emp_help'] = np.where(
        (merged_data['end_ue'] == 1) & (merged_data['t_till_emp'] <= 61),
        1,
        np.nan
    )

    # Create exit_emp variable (this part is simplified from the Stata code)
    merged_data['exit_emp'] = np.nan
    # Impute information to variable exit_emp
    merged_data.loc[(merged_data['exit_emp_help'] == 1) &
                  (merged_data['end_ue'] == 1) &
                  (merged_data['exit_emp'].isna()), 'exit_emp'] = 3

    # Drop auxiliary variables
    merged_data = merged_data.drop(['exit_emp_help', 't_till_emp_help', 'next_employed_date_help'], axis=1)

    # 4.2 Flag STUE and LTUE populations
    # Flag ASU spells that belong to episode of long-term unemployment
    merged_data['ltue'] = np.where(
        (merged_data['ue_duration'] >= 365) & (~merged_data['ue_duration'].isna()),
        1,
        0
    )

    # Flag start of long-term unemployment
    merged_data['beg_ltue'] = np.where(
        (merged_data['beg_ue'] == 1) & (merged_data['ltue'] == 1),
        1,
        np.nan
    )

    # Prepare data for further steps
    # Copy start and end date of unemployment to all parallel spells
    merged_data['quelle_gr_help'] = np.where(merged_data['quelle_gr'] == 5, 0, merged_data['quelle_gr'])

    # Sort for the fill operation
    merged_data = merged_data.sort_values(['persnr', 'begepi', 'quelle_gr_help'])

    # Create a grouping key
    merged_data['group_key'] = merged_data['persnr'].astype(str) + '_' + merged_data['begepi'].astype(str)

    # Fill beg_ue_date and end_ue_date within groups
    for col in ['beg_ue_date', 'end_ue_date', 'ue_duration']:
        merged_data[col] = merged_data.groupby('group_key')[col].transform(
            lambda x: x.fillna(method='ffill')
        )

    # Drop the temporary group_key
    merged_data = merged_data.drop(['group_key', 'quelle_gr_help'], axis=1)

    # Standard sorting
    merged_data = merged_data.sort_values(['persnr', 'spell'])

    # Add English labels (these are stored as attributes in pandas)
    label_dict_en = {
        'year': 'Year of episode',
        'age': 'Age',
        'beg_ue': 'Begin of unemployment (ASU spell)',
        'beg_ue_date': 'Start date of UE episode',
        'end_ue': 'End of unemployment (ASU spell)',
        'seeking1': 'Seeking for employment while unemployed spell',
        't_since_seeking': 'Time since last UE & job seeking episode',
        't_since_asu': 'Time since last ASU spell (that does not pause UE)',
        'ue_duration': 'Duration of UE/AS-Episode',
        'ltue': 'Long-term unemployment (bin. var)'
    }

    # Add German labels
    label_dict_de = {
        'year': 'Jahr (Episode)',
        'age': 'Alter',
        'beg_ue': 'Start Arbeitslosigkeit(ASU spell)',
        'beg_ue_date': 'Start date of UE episode',
        'end_ue': 'Ende Arbeitslosigkeit(ASU spell)',
        'seeking1': 'Arbeitssuchend-Spell (enge Def.)',
        't_since_seeking': 'Tage seit letzter UE/AS-Episode',
        't_since_asu': 'Tage seit letztem ASU spell',
        'ue_duration': 'Dauer der UE/AS-Episode',
        'ltue': 'Langzeitsarbeitslosigkeit (bin. Var)'
    }

    # Applying labels as column attributes (this is metadata and doesn't affect calculations)
    for col, label in label_dict_en.items():
        if col in merged_data.columns:
            merged_data[col].attrs['label_en'] = label

    for col, label in label_dict_de.items():
        if col in merged_data.columns:
            merged_data[col].attrs['label_de'] = label

    # Return the processed data for use in the master script
    return merged_data

if __name__ == "__main__":
    # This script should be run as part of the master SIAB processing pipeline
    print("This script should be run as part of the master SIAB processing pipeline")