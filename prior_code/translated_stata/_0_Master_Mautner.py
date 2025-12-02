#!/usr/bin/env python3
# ------------------------------------------------------------------------------------------------#
#                                MASTER SCRIPT FOR SIAB DATA PREPARATION
# ------------------------------------------------------------------------------------------------#

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
from config import ORIG_DIR, DATA_DIR, DATANAME, create_directories

# Import processing functions from each module
from _01_Identify_unemployment_Mautner import process_unemployment
from _02_SIAB_bio_Mautner import process_biography
from _03a_Establishment_info_20180515_Mautner import process_establishments
from _03b_industries_1digit_destatis_Mautner import process_industries
from _03c_industries_1digit_iab_Mautner import map_industries
from _03d_occ_blossfeld_Mautner import process_occupations
from _03e_educ_imputation_Mautner import process_education
from _03f_wages_deflation_Mautner import process_wages
from _04_Index_entries_Mautner import process_entries
from _05_Employment_history_Mautner import process_employment
from _06_Reshape_data_Mautner import process_reshape

# Remove redundant configuration
create_directories()  # Create required directories


def main():
    """Execute the complete SIAB data processing workflow."""
    print("Starting SIAB data processing...")

    # Load initial data
    siab_data = pd.read_stata(os.path.join(ORIG_DIR, f"{DATANAME}.dta"))
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
    siab_data.to_stata(os.path.join(DATA_DIR, "beforereshaping.dta"))

    # 4. Process unemployment entries
    siab_data = process_entries(siab_data)

    # Save before loop processing
    siab_data.to_stata(os.path.join(DATA_DIR, "beforeloop.dta"))

    # 5. Process each entry
    master_data = None
    for entry_num in range(1, 16):
        print(f"Processing entry {entry_num}")

        # Load fresh data for each iteration except first
        if entry_num > 1:
            siab_data = pd.read_stata(os.path.join(DATA_DIR, "beforeloop.dta"))

        # Tag relevant unemployment entry
        siab_data["relevant_ue"] = np.where(
            siab_data["nrEntry"] == entry_num, 1, np.nan
        )
        siab_data["ue_pop"] = siab_data.groupby("persnr")["relevant_ue"].transform(
            "max"
        )
        entry_data = siab_data[siab_data["ue_pop"] == 1].copy()

        # Process employment history
        entry_data = process_employment(entry_data)
        entry_data.to_stata(os.path.join(DATA_DIR, f"beforedropping{entry_num}.dta"))

        # Reshape data
        entry_data = process_reshape(entry_data)
        entry_data.to_stata(os.path.join(DATA_DIR, f"ready_entry{entry_num}.dta"))

        # Append to master data
        if master_data is None:
            master_data = entry_data
        else:
            master_data = pd.concat([master_data, entry_data], ignore_index=True)

    # Save final dataset
    master_data.to_stata(os.path.join(DATA_DIR, "_forR.dta"))
    print("Data processing complete!")


if __name__ == "__main__":
    main()
