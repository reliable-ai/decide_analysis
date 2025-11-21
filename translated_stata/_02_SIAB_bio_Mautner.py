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


def process_biography(df):
    """Process biographical variables from longitudinal SIAB data.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with added biographical variables
    """
    # Create observation counters
    df["level1"] = (
        df.groupby(["persnr", "begepi", "quelle_gr"])["spell"].rank(method="first") - 1
    )
    df["level2"] = df.groupby(["persnr", "begepi"])["spell"].rank(method="first") - 1

    # Tag vocational training, interns, and minijobs
    df["azubi"] = (df["erwstat"] == 2).astype(int)
    df["intern"] = (df["erwstat"] == 5).astype(int)
    df["minijob"] = (df["erwstat"] == 3).astype(int)

    # Employment groups (5 categories)
    df["pg5"] = pd.NA
    df.loc[df["erwstat"] == 1, "pg5"] = 1  # standard
    df.loc[df["erwstat"] == 12, "pg5"] = 2  # azubis
    df.loc[df["erwstat"] == 14, "pg5"] = 3  # altersteilzeit
    df.loc[df["erwstat"] == 13, "pg5"] = 4  # mini-job
    df.loc[df["pg5"].isna(), "pg5"] = 5  # all other

    # Employment versions (1-3)
    df["emp1_sp"] = ((df["azubi"] != 1) & (df["quelle_gr"] == 1)).astype(int)
    df["emp2_sp"] = (
        (df["azubi"] != 1) & (df["intern"] != 1) & (df["quelle_gr"] == 1)
    ).astype(int)
    df["emp3_sp"] = (
        (df["azubi"] != 1)
        & (df["intern"] != 1)
        & (df["minijob"] != 1)
        & (df["quelle_gr"] == 1)
    ).astype(int)

    # First day in employment calculations
    for i in range(1, 4):
        emp_col = f"emp{i}_sp"
        ein_col = f"ein_erw{i}"
        df[ein_col] = pd.NA

        # Group by person and get first employment date
        first_emp = df[df[emp_col] == 1].groupby("persnr")["begepi"].transform("min")
        df.loc[df[emp_col] == 1, ein_col] = first_emp

    # Calculate days in employment
    for i in range(1, 4):
        emp_col = f"emp{i}_sp"
        tage_col = f"tage_erw{i}_kum"

        df[tage_col] = (
            df[df[emp_col] == 1]
            .groupby("persnr")
            .apply(lambda x: (x["endepi"] - x["begepi"] + 1).cumsum())
        )

    # Parallel jobs processing
    # ... existing code for parallel jobs processing ...

    # First day and days in establishment
    df["ein_bet"] = df.groupby("bnn")["begepi"].transform("min")
    df["tage_bet_kum"] = df.groupby("bnn").apply(
        lambda x: (x["endepi"] - x["begepi"] + 1).cumsum()
    )

    # Job history processing
    # ... existing code for job history ...

    # Benefit receipt processing (LeH and LHG)
    for source in ["leh", "lhg"]:
        quelle = 2 if source == "leh" else 3
        df[f"lst_{source}"] = (df["quelle_gr"] == quelle).astype(int)

        # Calculate benefit durations and counts
        # ... existing code for benefit calculations ...

    # Subsidized employment
    df["se_ep"] = ((df["quelle_gr"] == 4) & df["erwstat"].isin([41, 44])).astype(int)

    # Label variables and handle missing values
    # ... existing code for labels and missing values ...

    # Save processed data
    output_path = "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/siab_r_7517_v1_sample_bio_HM.dta"
    df.to_stata(output_path, write_index=False)

    return df


if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
