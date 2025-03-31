#!/usr/bin/env python3
#------------------------------------------------------------------------------------------------#
#                                MASTER SCRIPT FOR SIAB DATA PREPARATION
#------------------------------------------------------------------------------------------------#

"""
Authors:         Hannah Mautner (original Stata code)
                 Converted to Python
Date:            20180507 (original)
SIAB version:    7514 v1

This script orchestrates the entire data processing workflow for SIAB data.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

# Import processing functions from each module
from identify_unemployment_Mautner import process_unemployment
from siab_bio_Mautner import process_biography
from establishment_info_Mautner import process_establishments
from industries_1digit_destatis_Mautner import process_industries
from industries_1digit_iab_Mautner import map_industries
from occ_blossfeld_Mautner import process_occupations
from educ_imputation_Mautner import process_education
from wages_deflation_Mautner import process_wages
from index_entries_Mautner import process_entries
from employment_history_Mautner import process_employment
from reshape_data_Mautner import process_reshape

# --------------------------------------
# PATHS CONFIGURATION
base_dir = "/Users/ruben/Downloads/FinaleVersionUnterlagen"
log_dir = f"{base_dir}/log"
orig_dir = f"{base_dir}/orig/siab_r_7517_v1_stata"
data_dir = f"{base_dir}/data"

# Ensure directories exist
for directory in [log_dir, data_dir]:
    os.makedirs(directory, exist_ok=True)

# --------------------------------------
# FILENAMES AND SETTINGS
date_str = "20180706_samp"
dataname = "siab_r_7517_v1"
logname = "siab_7514_v1_prep"

def main():
    """Execute the complete SIAB data processing workflow."""
    print("Starting SIAB data processing...")

    # Load initial data
    siab_data = pd.read_stata(os.path.join(orig_dir, f"{dataname}.dta"))
    print(f"Loaded {len(siab_data)} records.")

    # 1. Process unemployment episodes
    siab_data = process_unemployment(siab_data)

    # 2. Process biographical variables
    siab_data = process_biography(siab_data)

    # 3. Further data preparation
    # 3a. Add establishment information
    siab_data = process_establishments(siab_data)

    # 3b-c. Process industry classifications
    siab_data = process_industries(siab_data)
    siab_data = map_industries(siab_data)

    # 3d. Process occupations
    siab_data = process_occupations(siab_data)

    # 3e. Process education
    siab_data = process_education(siab_data)

    # 3f. Process wages
    siab_data = process_wages(siab_data)

    # Save intermediate state
    siab_data.to_stata(os.path.join(data_dir, "beforereshaping.dta"))

    # 4. Process unemployment entries
    siab_data = process_entries(siab_data)

    # Save before loop processing
    siab_data.to_stata(os.path.join(data_dir, "beforeloop.dta"))

    # 5. Process each entry
    master_data = None
    for entry_num in range(1, 16):
        print(f"Processing entry {entry_num}")

        # Load fresh data for each iteration except first
        if entry_num > 1:
            siab_data = pd.read_stata(os.path.join(data_dir, "beforeloop.dta"))

        # Tag relevant unemployment entry
        siab_data['relevant_ue'] = np.where(siab_data['nrEntry'] == entry_num, 1, np.nan)
        siab_data['ue_pop'] = siab_data.groupby('persnr')['relevant_ue'].transform('max')
        entry_data = siab_data[siab_data['ue_pop'] == 1].copy()

        # Process employment history
        entry_data = process_employment(entry_data)
        entry_data.to_stata(os.path.join(data_dir, f"beforedropping{entry_num}.dta"))

        # Reshape data
        entry_data = process_reshape(entry_data)
        entry_data.to_stata(os.path.join(data_dir, f"ready_entry{entry_num}.dta"))

        # Append to master data
        if master_data is None:
            master_data = entry_data
        else:
            master_data = pd.concat([master_data, entry_data], ignore_index=True)

    # Save final dataset
    master_data.to_stata(os.path.join(data_dir, "_forR.dta"))
    print("Data processing complete!")

if __name__ == "__main__":
    main()