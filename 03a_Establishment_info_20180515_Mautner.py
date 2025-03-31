#!/usr/bin/env python3
"""
MERGE ESTABLISHMENT INFORMATION
Author: Hannah Mautner (original Stata code)
       Converted to Python
Purpose: Add establishment level information from BHP data
"""
import pandas as pd
import numpy as np
import os

def add_establishment_info(siab_data):
    """Add establishment information to SIAB data."""

    # Rename year column for merge
    siab_data = siab_data.rename(columns={'year': 'jahr'})

    # Load and merge BHP data
    bhp_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/orig/SIAB_7514_v1_bhp_basis_v1.dta"
    bhp_data = pd.read_stata(bhp_path, columns=['betnr', 'jahr', 'az_ges', 'az_vz', 'az_gf', 'ao_kreis'])

    # Merge on establishment and year
    merged_data = pd.merge(
        siab_data,
        bhp_data,
        on=['betnr', 'jahr'],
        how='left',
        indicator=True
    )

    # Keep only matched records and non-BeH spells
    merged_data = merged_data[
        (merged_data['_merge'].isin([1, 3])) | (merged_data['quelle_gr'] > 1)
    ]

    # Replace missing values with 0 for employment variables
    for col in ['az_ges', 'az_vz', 'az_gf']:
        merged_data[col] = merged_data[col].fillna(0)

    # Create Eastern Germany indicator
    merged_data['Ieast'] = (merged_data['ao_kreis'] >= 11000).astype('int8')

    # Add variable labels
    merged_data['Ieast'].attrs['label'] = "Establishment in Eastern Germany"

    # Clean up and rename columns back
    merged_data = merged_data.drop('_merge', axis=1)
    merged_data = merged_data.rename(columns={'jahr': 'year'})

    # Save processed data
    output_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/siab_r_7517_v1_sample_estab.dta"
    merged_data.to_stata(output_path, write_index=False)

    return merged_data

if __name__ == "__main__":
    # Load the SIAB data
    data_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/siab_r_7517_v1_sample_bio_HM.dta"
    if os.path.exists(data_path):
        siab_data = pd.read_stata(data_path)
        add_establishment_info(siab_data)
    else:
        print(f"Data file not found: {data_path}")
