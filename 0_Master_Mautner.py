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
import subprocess

# --------------------------------------
# PATHS CONFIGURATION

# Define the base directories
log_dir = "/Users/ruben/Downloads/FinaleVersionUnterlagen/log"
orig_dir = "/Users/ruben/Downloads/FinaleVersionUnterlagen/orig/siab_r_7517_v1_stata/"
data_dir = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/"
prog_dir = "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Python/"  # Changed from Stata to Python

# Ensure directories exist
for directory in [log_dir, data_dir, prog_dir]:
    os.makedirs(directory, exist_ok=True)

# --------------------------------------
# DATE MACRO
date_str = "20180706_samp"

# --------------------------------------
# FILENAMES
dataname = "siab_r_7517_v1"
logname = "siab_7514_v1_prep"

# --------------------------------------
# LOGGING SETUP
log_file = os.path.join(log_dir, f"{logname}_{date_str}.log")
print(f"Log file will be created at: {log_file}")

# --------------------------------------
# MAIN WORKFLOW

def run_script(script_name):
    """Execute a Python script and handle any errors."""
    script_path = os.path.join(prog_dir, script_name)
    print(f"Running {script_path}...")
    try:
        # In a real implementation, you might use importlib or subprocess
        # Here we'll use exec to run the script in the current context
        with open(script_path, 'r') as file:
            exec(file.read())
        print(f"Completed {script_name}")
    except Exception as e:
        print(f"Error executing {script_name}: {e}")

# Read in SIAB data
print("Loading SIAB data...")
siab_data = pd.read_stata(os.path.join(orig_dir, f"{dataname}.dta"))
print(f"Loaded {len(siab_data)} records.")

# 1. Identification of job seeking episodes and long-term unemployment
print("\n1. Identifying unemployment episodes...")
run_script("01_Identify_unemployment_Mautner.py")

# 2. Creation of biographical variables
print("\n2. Creating biographical variables...")
run_script("02_SIAB_bio_Mautner.py")

# 3. Further data preparation
print("\n3. Preparing additional data...")

# 3a. Merge BHP data
run_script("03a_Establishment_info_20180515_Mautner.py")

# 3b-c. Generate 1-digit industry variables
run_script("03b_industries_1digit_destatis_Mautner.py")
run_script("03c_industries_1digit_iab_Mautner.py")

# 3d. Blossfeld occupation
run_script("03d_occ_blossfeld_Mautner.py")

# 3e. Imputation of education
run_script("03e_educ_imputation_HM_Mautner.py")

# 3f. Wages deflation
run_script("03f_wages_deflation_Mautner.py")

# Save intermediate data
print("Saving intermediate data before reshaping...")
siab_data.to_stata(os.path.join(data_dir, "beforereshaping.dta"), write_index=False)

# 4. Creation of variables for supervised learning models
print("\n4. Creating variables for supervised learning models...")
siab_data = pd.read_stata(os.path.join(data_dir, "beforereshaping.dta"))

# Index entries into unemployment
run_script("04_Index_entries_Mautner.py")

# Save data before loop
siab_data.to_stata(os.path.join(data_dir, "beforeloop.dta"), write_index=False)

# 5. Loop over entries into unemployment
print("\n5. Processing unemployment entries...")
for i in range(1, 16):  # Loops from 1 to 15
    print(f"Processing entry {i}")

    if i != 1:
        # Get raw data for entries after the first one
        siab_data = pd.read_stata(os.path.join(data_dir, "beforeloop.dta"))

    # Tag unemployment entry relevant for this iteration
    siab_data['relevant_ue'] = np.nan
    siab_data.loc[siab_data['nrEntry'] == i, 'relevant_ue'] = 1

    # Tag all individuals with relevant entry
    ue_pop = siab_data.groupby('persnr')['relevant_ue'].max()
    siab_data = siab_data.merge(ue_pop.rename('ue_pop'), on='persnr', how='left')

    # Keep only individuals with (at least) one entry into unemployment
    siab_data = siab_data[siab_data['ue_pop'] == 1]

    # Generate employment history for relevant entry
    run_script("05_Employment_history_Mautner.py")

    # Save before reshaping data for entry i
    siab_data.to_stata(os.path.join(data_dir, f"beforedropping{i}.dta"), write_index=False)

    # Reshape data: Drop variables and spells not necessary for models
    run_script("06_Reshape_data_Mautner.py")

    # Save reshaped data for entry i
    siab_data.to_stata(os.path.join(data_dir, f"ready_entry{i}.dta"), write_index=False)

# Append data for all entries
print("\n6. Combining all entry data...")
combined_data = pd.read_stata(os.path.join(data_dir, "ready_entry1.dta"))

for i in range(2, 16):  # Loops from 2 to 15
    entry_data = pd.read_stata(os.path.join(data_dir, f"ready_entry{i}.dta"))
    combined_data = pd.concat([combined_data, entry_data], ignore_index=True)

# Save final data set
combined_data.to_stata(os.path.join(data_dir, "_forR.dta"), write_index=False)

print("Data processing complete!")