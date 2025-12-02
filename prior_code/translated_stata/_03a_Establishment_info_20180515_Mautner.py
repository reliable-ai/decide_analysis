#!/usr/bin/env python3
"""
MERGE ESTABLISHMENT INFORMATION
Author: Hannah Mautner (original Stata code)
       Converted to Python
Purpose: Add establishment level information from BHP data
"""

import pandas as pd


def process_establishments(df):
    """Add establishment information from BHP data to SIAB records.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with added establishment information
    """
    # Rename year column for merge
    df = df.rename(columns={"year": "jahr"})

    # Load and merge BHP data
    bhp_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/orig/SIAB_7514_v1_bhp_basis_v1.dta"
    bhp_data = pd.read_stata(
        bhp_path, columns=["betnr", "jahr", "az_ges", "az_vz", "az_gf", "ao_kreis"]
    )

    # Merge on establishment and year
    merged_data = pd.merge(
        df, bhp_data, on=["betnr", "jahr"], how="left", indicator=True
    )

    # Keep only matched records and non-BeH spells
    merged_data = merged_data[
        (merged_data["_merge"].isin([1, 3])) | (merged_data["quelle_gr"] > 1)
    ]

    # Replace missing values with 0 for employment variables
    for col in ["az_ges", "az_vz", "az_gf"]:
        merged_data[col] = merged_data[col].fillna(0)

    # Create Eastern Germany indicator
    merged_data["Ieast"] = (merged_data["ao_kreis"] >= 11000).astype("int8")

    # Add variable labels
    merged_data["Ieast"].attrs["label"] = "Establishment in Eastern Germany"

    # Clean up and rename columns back
    merged_data = merged_data.drop("_merge", axis=1)
    merged_data = merged_data.rename(columns={"jahr": "year"})

    return merged_data


if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
