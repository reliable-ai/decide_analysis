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
    df["deutsch"] = df["deutsch"].replace({99999: -1, ".a": -2})
    df["maxdeutsch"] = df.groupby("persnr")["deutsch"].transform("max")

    # Handle missings for ausbildung_imp
    df["ausbildung_imp"] = df["ausbildung_imp"].replace({99999: -1})
    df["maxausbildung_imp"] = df.groupby("persnr")["ausbildung_imp"].transform("max")

    # Handle missings for schule
    df["schule"] = df["schule"].replace({".n": -1, ".z": -2})
    df["maxschule"] = df.groupby("persnr")["schule"].transform("max")

    # Handle missings for niveau
    df["niveau"] = df["niveau"].replace({".n": -1, ".z": -2})
    df["maxniveau"] = df.groupby("persnr")["niveau"].transform("max")

    # Create Bundesland mapping
    def map_to_bula(x):
        if pd.isna(x):
            return np.nan
        x = int(x)
        for i in range(1, 17):
            if x < (i + 1) * 1000 and x >= i * 1000:
                return i
        return np.nan

    df["bula"] = df["ao_reg"].apply(map_to_bula)

    # Fix: Get most recent Bundesland (using the preserve-restore pattern from Stata)
    bula_latest = (
        df[~df["bula"].isna()]
        .sort_values(["persnr", "begepi"])
        .groupby("persnr")
        .last()[["bula"]]
        .rename(columns={"bula": "maxbula"})
    )
    df = pd.merge(df, bula_latest, on="persnr", how="left")

    # Fix: Handle pendler (commuter) information correctly
    df["pendler"] = df["pendler"].replace({".n": -1, ".z": -2})
    # Using the preserve-restore pattern from Stata
    pendler_latest = (
        df[df["pendler"] > 0]
        .sort_values(["persnr", "begepi"])
        .groupby("persnr")
        .last()[["pendler"]]
        .rename(columns={"pendler": "maxpendler"})
    )
    df = pd.merge(df, pendler_latest, on="persnr", how="left")

    # Fix: Handle industry sector information correctly
    df["w08_gen_gr"] = df["w08_gen_gr"].replace({".n": -1, ".z": -2})
    # Using the preserve-restore pattern from Stata
    industry_latest = (
        df[df["w08_gen_gr"] > 0]
        .sort_values(["persnr", "begepi"])
        .groupby("persnr")
        .last()[["w08_gen_gr"]]
        .rename(columns={"w08_gen_gr": "lastw08_gen_gr"})
    )
    df = pd.merge(df, industry_latest, on="persnr", how="left")

    # Keep only unemployment entry spells
    df = df[df["relevant_ue"] == 1].copy()

    # Create variable groups for organization
    variable_groups = {
        "response": ["ltue"],
        "spell_original": [
            "persnr",
            "year",
            "quelle_gr",
            "begepi",
            "endepi",
            "alo_dau",
        ],
        "spell_generated": ["ue_pop", "nrEntry", "beg_ue", "ue_duration"],
        "status_before": [
            "employed_before",
            "receipt_leh_before",
            "receipt_lhg_before",
            "se_before",
            "ASU_notue_seeking_before",
            "ASU_other_before",
            "break_before",
        ],
        "lastcontact_lm": [
            "tsince_ein_erw1",
            "tsince_ein_erw1_cat",
            "tsince_ft_lm_contact",
            "tsince_lm_contact",
            "tsince_lm_contact_cat",
            "tsince_ft_lm_contact_cat",
        ],
        "emp_total": [
            "emp_total",
            "est_total",
            "emp1_total",
            "emp1_total_dur",
            "emp2_total_dur",
            "emp3_total_dur",
            "emp1_m_dur",
            "main_industry",
            "secjob_tot_dur",
            "minijob_tot_dur",
            "ft_tot_dur",
            "befrist_tot_dur",
            "leih_tot_dur",
        ],
        "lastjob": [
            "lastjob_none",
            "lastjob_tot_dur",
            "lastjob_parallel",
            "lastjob_type",
            "lastjob_pt",
            "lastjob_wage_defl",
            "lastjob_occblo",
            "lastjob_niveau",
            "lastjob_leih",
            "lastjob_befrist",
            "lastjob_educ",
            "lastjob_ao_kreis",
            "lastjob_industry_destatis",
        ],
        "lastjob_noinfo": [
            "lastjob_type_noinfo",
            "lastjob_parallel_noinfo",
            "lastjob_pt_noinfo",
            "lastjob_occblo_noinfo",
            "lastjob_niveau_noinfo",
            "lastjob_leih_noinfo",
            "lastjob_befrist_noinfo",
            "lastjob_educ_noinfo",
            "lastjob_ao_kreis_noinfo",
            "lastjob_industry_destatis_noinfo",
        ],
        "benefit_hist": [
            "LHG_total",
            "LHG_tot_dur",
            "LHG_m_dur",
            "LEH_total",
            "LEH_tot_dur",
            "LEH_m_dur",
        ],
        "almp_hist": [
            "almp_total",
            "almp_tot_dur",
            "almp_m_dur",
            "almp_aw_total",
            "almp_aw_tot_dur",
            "almp_aw_m_dur",
            "se_tot_dur",
        ],
        "seeking_hist": [
            "tsince_lastseeking",
            "tsince_lastseeking_cat",
            "seeking1_total",
            "seeking1_tot_dur",
            "seeking1_m_dur",
        ],
        "bio": [
            "age",
            "frau",
            "german",
            "ausbildung_imp",
            "togerman",
            "moves",
            "moves_noinfo",
            "relocated",
            "wo_east",
        ],
        "bio_imputed": [
            "age",
            "frau",
            "ausbildung_imp",
            "german",
            "togerman",
            "moves",
            "moves_noinfo",
            "relocated",
            "wo_east",
        ],
        "current_seeking": ["niveau"],
    }

    # Create final dataset with selected columns in proper order
    columns_to_keep = []
    for group in variable_groups.values():
        for column in group:
            if column not in columns_to_keep and column in df.columns:
                columns_to_keep.append(column)

    # Add the newly created max/last variables
    additional_cols = [
        "maxdeutsch",
        "maxausbildung_imp",
        "maxbula",
        "maxniveau",
        "maxschule",
        "maxpendler",
        "lastw08_gen_gr",
    ]
    for col in additional_cols:
        if col not in columns_to_keep and col in df.columns:
            columns_to_keep.append(col)

    # Select final columns and add labels
    df_final = df[columns_to_keep].copy()

    # Fix: Add labels for documentation (using pd.Series for column descriptions)
    variable_labels = {
        "ltue": "Long-term unemployment status: 0=Not_LTUE, 1=LTUE",
        "maxdeutsch": "most recent nationality, neg.value=mis",
        "maxausbildung_imp": "most recent education, neg.value=mis",
        "maxschule": "most recent school education, neg.value=mis",
        "maxniveau": "most recent niveau of job, neg.value=mis",
        "maxbula": "most recent Bundesland",
        "maxpendler": "most recent commute",
        "lastw08_gen_gr": "most recent sector",
        "employed_before": "Any employment in 6 weeks before entry to unemployment",
        "receipt_leh_before": "LeH receipt in 6 weeks before entry to unemployment",
        "receipt_lhg_before": "LHG receipt in 6 weeks before entry to unemployment",
        "se_before": "Any subsidized employment in 6 weeks before entry to unemployment",
        "ASU_notue_seeking_before": "Registered as job seeking/ not UE in 6 weeks before entry to unemployment",
        "ASU_other_before": "Registered with ASU register for other reason in 6 weeks before entry to unemployment",
        "break_before": "No info about 6 weeks prior to entry to unemployment",
        "age": "Age at entry to unemployment",
        "german": "German nationality",
        "togerman": "Has changed nationality to German",
        "moves": "No. of private relocations between Kreise",
        "relocated": "Changed residence location since last job",
        "wo_east": "Current location residence in eastern Germany",
        # Can be expanded with more labels from the Stata file
    }

    # Store labels as DataFrame metadata (Python equivalent to Stata labels)
    for col, label in variable_labels.items():
        if col in df_final.columns:
            df_final[col].attrs["label"] = label

    return df_final


if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
