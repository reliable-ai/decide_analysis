# imports
import pandas as pd
import numpy as np


def reshape_data_for_ml(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reshapes data for supervised learning models. This function is based on
    Stata code provided by Hannah Mautner.

    The function generates predictor variables on person level
    (employment history, ASU history, benefit history, measures history,
    biographical variables, current job seeking characteristics), creates the
    response/outcome variable (long-term unemployment indicator), and labels
    and orders variables for machine learning analysis.

    Args:
        df (pd.DataFrame): Dataset containing unemployment entries and
            employment history variables. Expected columns include: person_id,
            spell_count, beg_ue, year, and various employment/biographical
            variables.

    Returns:
        pd.DataFrame: Reshaped dataset ready for machine learning with:
            only unemployment entry spells (relevant_ue == 1), all predictor
            variables aggregated to person level, response variable (ltue:
            long-term unemployment), and cleaned and labeled variables.
    """

    # work on copy of dataframe
    df = df.copy()

    ### JUDGMENT CALL: why impute missing values for key variables using max within person?
    # impute missing values for key variables using max within person
    for var in [
        "german_citizen",
        "education_level_imputed",
        "school_completed",
        "occupation_skill_level",
    ]:
        if var in df.columns:
            # recode special missing values
            df[var] = df[var].replace({99999: -1, np.nan: -2})
            df[f"max{var}"] = df.groupby("person_id")[var].transform("max")
            df[var] = df[var].replace({-1: 99999, -2: np.nan})
            df[f"max{var}"] = df[f"max{var}"].replace({-1: 99999, -2: np.nan})

    ### JUDGMENT CALL: why do we need a state variable?
    # create Bundesland (state) variable from district_region
    if "district_region" in df.columns:
        df["bula"] = np.nan
        df.loc[
            (df["district_region"] < 2000) & df["district_region"].notna(), "bula"
        ] = 1
        df.loc[
            (df["district_region"] >= 2000) & (df["district_region"] < 3000), "bula"
        ] = 2
        df.loc[
            (df["district_region"] >= 3000) & (df["district_region"] < 4000), "bula"
        ] = 3
        df.loc[
            (df["district_region"] >= 4000) & (df["district_region"] < 5000), "bula"
        ] = 4
        df.loc[
            (df["district_region"] >= 5000) & (df["district_region"] < 6000), "bula"
        ] = 5
        df.loc[
            (df["district_region"] >= 6000) & (df["district_region"] < 7000), "bula"
        ] = 6
        df.loc[
            (df["district_region"] >= 7000) & (df["district_region"] < 8000), "bula"
        ] = 7
        df.loc[
            (df["district_region"] >= 8000) & (df["district_region"] < 9000), "bula"
        ] = 8
        df.loc[
            (df["district_region"] >= 9000) & (df["district_region"] < 10000), "bula"
        ] = 9
        df.loc[
            (df["district_region"] >= 10000) & (df["district_region"] < 11000), "bula"
        ] = 10
        df.loc[
            (df["district_region"] >= 11000) & (df["district_region"] < 12000), "bula"
        ] = 11
        df.loc[
            (df["district_region"] >= 12000) & (df["district_region"] < 13000), "bula"
        ] = 12
        df.loc[
            (df["district_region"] >= 13000) & (df["district_region"] < 14000), "bula"
        ] = 13
        df.loc[
            (df["district_region"] >= 14000) & (df["district_region"] < 15000), "bula"
        ] = 14
        df.loc[
            (df["district_region"] >= 15000) & (df["district_region"] < 16000), "bula"
        ] = 15
        df.loc[df["district_region"] >= 16000, "bula"] = 16

        # get most recent bula
        bula_df = df[df["bula"].notna()].copy()
        bula_df = bula_df.sort_values(["person_id", "episode_start_date"])
        bula_df = (
            bula_df.groupby("person_id").last().reset_index()[["person_id", "bula"]]
        )
        bula_df.columns = ["person_id", "maxbula"]
        df = df.merge(bula_df, on="person_id", how="left")

    # similar process for commuter and wage_group
    for var in ["commuter", "wage_group"]:
        if var in df.columns:
            df[var] = df[var].replace({np.nan: -1, 99999: -2})
            var_df = df[df[var] > 0].copy()
            if len(var_df) > 0:
                var_df = var_df.sort_values(["person_id", "episode_start_date"])
                var_df = (
                    var_df.groupby("person_id").last().reset_index()[["person_id", var]]
                )
                var_df.columns = [
                    "person_id",
                    f"max{var}" if var != "wage_group" else "lastwage_group",
                ]
                df = df.merge(var_df, on="person_id", how="left")
            df[var] = df[var].replace({-1: np.nan, -2: 99999})

    # keep only unemployment entry spells
    df = df[df["relevant_ue"] == 1].copy()

    # response variable: long-term unemployment
    if "ltue" not in df.columns:
        df["ltue"] = (df["ue_duration"] >= 365).astype(int)
        df.loc[df["ue_duration"].isna(), "ltue"] = np.nan

    # ensure all necessary variables are present
    # if variables from employment history are missing, set to default values

    # fill missing values for various variable groups
    variable_groups = {
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
            "female",
            "german",
            "education_level_imputed",
            "togerman",
            "moves",
            "moves_noinfo",
            "relocated",
            "wo_east",
        ],
    }

    ### JUDGMENT CALL: is there another way to handle missing values?
    # fill missing values with appropriate defaults
    for group, vars_list in variable_groups.items():
        for var in vars_list:
            if var in df.columns:
                if var in [
                    "emp_total",
                    "est_total",
                    "emp1_total",
                    "LHG_total",
                    "LEH_total",
                    "almp_total",
                    "almp_aw_total",
                    "seeking1_total",
                    "moves",
                ]:
                    df[var] = df[var].fillna(0)
                elif var in [
                    "emp1_total_dur",
                    "emp2_total_dur",
                    "emp3_total_dur",
                    "emp1_m_dur",
                    "secjob_tot_dur",
                    "minijob_tot_dur",
                    "ft_tot_dur",
                    "befrist_tot_dur",
                    "leih_tot_dur",
                    "lastjob_tot_dur",
                    "lastjob_wage_defl",
                    "LHG_tot_dur",
                    "LHG_m_dur",
                    "LEH_tot_dur",
                    "LEH_m_dur",
                    "almp_tot_dur",
                    "almp_m_dur",
                    "almp_aw_tot_dur",
                    "almp_aw_m_dur",
                    "se_tot_dur",
                    "seeking1_tot_dur",
                    "seeking1_m_dur",
                ]:
                    df[var] = df[var].fillna(0)
                elif var in [
                    "main_industry",
                    "lastjob_type",
                    "lastjob_occblo",
                    "lastjob_niveau",
                    "lastjob_leih",
                    "lastjob_befrist",
                    "lastjob_educ",
                    "lastjob_ao_kreis",
                    "lastjob_industry_destatis",
                    "german",
                    "education_level_imputed",
                    "wo_east",
                    "relocated",
                ]:
                    df[var] = df[var].fillna(99999)
                elif var in [
                    "lastjob_parallel",
                    "lastjob_pt",
                    "employed_before",
                    "receipt_leh_before",
                    "receipt_lhg_before",
                    "se_before",
                    "ASU_notue_seeking_before",
                    "ASU_other_before",
                    "break_before",
                    "togerman",
                    "moves_noinfo",
                ]:
                    df[var] = df[var].fillna(0)
                elif var in [
                    "tsince_lastseeking_cat",
                    "tsince_lm_contact_cat",
                    "tsince_ft_lm_contact_cat",
                    "tsince_ein_erw1_cat",
                ]:
                    df[var] = df[var].fillna(99999)

    ### JUDGMENT CALL: why these features in particular?
    # select final variables to keep
    spell_original = [
        "person_id",
        "year",
        "spell_source",
        "episode_start_date",
        "episode_end_date",
        "unemployment_duration_days",
    ]
    spell_generated = ["ue_pop", "nrEntry", "beg_ue", "ue_duration"]

    # keep all variables from variable groups plus response and imputed max variables
    keep_vars = spell_original + spell_generated + ["ltue"]

    for group_vars in variable_groups.values():
        keep_vars.extend([v for v in group_vars if v in df.columns])

    # add max variables
    max_vars = [v for v in df.columns if v.startswith("max") or v.startswith("last")]
    keep_vars.extend(max_vars)

    # add current seeking variables
    if "occupation_skill_level" in df.columns:
        keep_vars.append("occupation_skill_level")

    # keep only variables that exist in dataframe
    keep_vars = [v for v in keep_vars if v in df.columns]

    # drop duplicates in keep_vars
    keep_vars = list(set(keep_vars))

    df_final = df[keep_vars].copy()

    # order variables
    ordered_vars = spell_original + spell_generated + ["ltue"]
    for group_name, group_vars in variable_groups.items():
        ordered_vars.extend([v for v in group_vars if v in df_final.columns])
    ordered_vars.extend([v for v in max_vars if v in df_final.columns])
    if "occupation_skill_level" in df_final.columns:
        ordered_vars.append("occupation_skill_level")

    # reorder columns
    existing_ordered = [v for v in ordered_vars if v in df_final.columns]
    remaining_cols = [v for v in df_final.columns if v not in existing_ordered]
    # drop duplicates in reordered columns
    final_vars = list(dict.fromkeys(existing_ordered + remaining_cols))

    df_final = df_final[final_vars].copy()

    return df_final
