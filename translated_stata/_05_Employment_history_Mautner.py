"""
SIAB Preparation
Employment History Processing

Creates employment history variables for individuals in the dataset.
Processes various aspects of employment including durations, types, and characteristics.

Author: Hannah Mautner
Converted to Python
"""

import numpy as np


def process_employment(df):
    """Process employment history for all individuals.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with added employment history information
    """
    # Initialize tracking variables
    df["lhgspell"] = df["quelle_gr"] == 3
    df["behspell"] = df["quelle_gr"] == 1
    df["lehspell"] = df["quelle_gr"] == 2
    df["asuspell"] = df["quelle_gr"] == 5
    df["mthspell"] = df["quelle_gr"] == 4

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
    df["status_beg_date"] = df.groupby("persnr")["begepi"].transform("max")

    # Calculate time since previous spell
    df["t_since_spell"] = df["beg_relevant_ue_date"] - df["endepi"] + 1

    # Create status indicators for 6 weeks prior
    status_window = df["t_since_spell"] <= 42
    for status in ["employed", "receipt_leh", "receipt_lhg", "se", "ASU_notue_seeking"]:
        df[f"{status}_before"] = (
            df.groupby("persnr")[status].transform("max").where(status_window, 0)
        )

    return df


def process_employment_counts(df):
    """Process counts and durations of different employment types."""
    # Filter to employment spells
    emp_spells = df[df["behspell"]].copy()

    # Count unique jobs
    df["emp_total"] = emp_spells.groupby("persnr")["ein_job"].nunique()

    # Calculate employment durations
    duration_cols = ["emp1_total_dur", "emp2_total_dur", "emp3_total_dur"]
    for i, col in enumerate(duration_cols, 1):
        df[col] = emp_spells.groupby("persnr")[f"tage_erw{i}_kum"].transform("max")

    return df


def process_industry_info(df):
    """Process industry information for individuals."""
    # Create helper variable for job duration calculation
    emp_spells = df[df["behspell"]].copy()

    # Calculate total duration in each industry
    industry_durations = (
        emp_spells.groupby(["persnr", "indust"])["tage_job_kum"].max().reset_index()
    )

    # Find main industry (the one with longest duration)
    main_industry = industry_durations.loc[
        industry_durations.groupby("persnr")["tage_job_kum"].idxmax()
    ]
    main_industry = main_industry[["persnr", "indust"]].rename(
        columns={"indust": "main_industry"}
    )

    # Calculate duration in each industry (industry1_destatis_tot_dur_*)
    industry_totals = {}
    for ind in range(1, 15):  # Industries 1-14
        ind_duration = industry_durations[industry_durations["indust"] == ind].copy()
        if not ind_duration.empty:
            ind_duration = ind_duration[["persnr", "tage_job_kum"]].rename(
                columns={"tage_job_kum": f"industry1_destatis_tot_dur_{ind}"}
            )
            industry_totals[ind] = ind_duration

    # Merge main industry info back to main dataframe
    df = df.merge(main_industry, on="persnr", how="left")

    # Merge individual industry durations
    for ind, ind_df in industry_totals.items():
        df = df.merge(ind_df, on="persnr", how="left")
        df[f"industry1_destatis_tot_dur_{ind}"] = df[
            f"industry1_destatis_tot_dur_{ind}"
        ].fillna(0)

    # Handle missing values
    df["main_industry"] = df["main_industry"].fillna(99999)

    return df


def process_last_job(df):
    """Process information about the last job before unemployment."""
    # Find end date of last job before current unemployment episode
    emp_spells = df[df["behspell"]].copy()

    # Tag last job before unemployment
    emp_spells["last_job_end"] = False

    # Sort by employment end date in descending order
    emp_spells = emp_spells.sort_values(["persnr", "endepi"], ascending=[True, False])

    # Take the first job for each person (latest end date)
    last_jobs = emp_spells.groupby("persnr").first().reset_index()

    # Mark the last job in the original dataframe
    last_job_markers = last_jobs[["persnr", "endepi"]].copy()
    last_job_markers["last_job_end"] = True

    df = df.merge(last_job_markers, on=["persnr", "endepi"], how="left")
    df["last_job_end"] = df["last_job_end"].fillna(False)

    # Extract last job characteristics
    last_job_info = last_jobs[
        [
            "persnr",
            "tage_job_kum",
            "pg5",
            "teilzeit",
            "wage_defl",
            "occ_blo",
            "niveau",
            "leih",
            "befrist",
            "ausbildung_imp",
            "ao_region",
            "indust",
        ]
    ].copy()

    # Rename the columns to match the Stata version
    rename_dict = {
        "tage_job_kum": "lastjob_tot_dur",
        "pg5": "lastjob_type",
        "teilzeit": "lastjob_pt",
        "wage_defl": "lastjob_wage_defl",
        "occ_blo": "lastjob_occblo",
        "niveau": "lastjob_niveau",
        "leih": "lastjob_leih",
        "befrist": "lastjob_befrist",
        "ausbildung_imp": "lastjob_educ",
        "ao_region": "lastjob_ao_kreis",
        "indust": "lastjob_industry_destatis",
    }

    last_job_info = last_job_info.rename(columns=rename_dict)

    # Check for parallel jobs
    last_job_dates = last_jobs[["persnr", "begepi", "endepi"]].copy()
    parallel_jobs = emp_spells.merge(
        last_job_dates, on=["persnr"], suffixes=("", "_last")
    )
    parallel_jobs = parallel_jobs[
        (parallel_jobs["begepi"] <= parallel_jobs["endepi_last"])
        & (parallel_jobs["endepi"] >= parallel_jobs["begepi_last"])
    ]

    parallel_job_counts = (
        parallel_jobs.groupby("persnr").size().reset_index(name="job_count")
    )
    parallel_job_counts["lastjob_parallel"] = parallel_job_counts["job_count"] > 1
    parallel_job_counts = parallel_job_counts[["persnr", "lastjob_parallel"]]

    # Merge last job info back to main dataframe
    df = df.merge(last_job_info, on="persnr", how="left")
    df = df.merge(parallel_job_counts, on="persnr", how="left")

    # Fill missing values
    for col in rename_dict.values():
        if col in ["lastjob_tot_dur", "lastjob_wage_defl"]:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna(99999)

    df["lastjob_parallel"] = df["lastjob_parallel"].fillna(False)
    df["lastjob_none"] = df["lastjob_tot_dur"] == 0

    return df


def process_employment_types(df):
    """Process various employment types and their durations."""
    # Calculate cumulated time in various employment types

    # Minijob duration
    minijob_spells = df[(df["behspell"]) & (df["minijob"] == 1)].copy()
    if not minijob_spells.empty:
        minijob_duration = (
            minijob_spells.groupby("persnr")
            .apply(lambda x: (x["endepi"] - x["begepi"] + 1).sum())
            .reset_index(name="minijob_tot_dur")
        )
        df = df.merge(minijob_duration, on="persnr", how="left")
        df["minijob_tot_dur"] = df["minijob_tot_dur"].fillna(0)
    else:
        df["minijob_tot_dur"] = 0

    # Part-time employment duration
    pt_spells = df[(df["behspell"]) & (df["teilzeit"] == 1)].copy()
    if not pt_spells.empty:
        pt_duration = (
            pt_spells.groupby("persnr")
            .apply(lambda x: (x["endepi"] - x["begepi"] + 1).sum())
            .reset_index(name="ft_tot_dur")
        )
        df = df.merge(pt_duration, on="persnr", how="left")
        df["ft_tot_dur"] = df["ft_tot_dur"].fillna(0)
    else:
        df["ft_tot_dur"] = 0

    # Secondary job duration
    df["secjob_tot_dur"] = (
        df.groupby("persnr")["tage_pjobs_kum"].transform("max").fillna(0)
    )

    # Fixed-term employment duration
    befrist_spells = df[(df["behspell"]) & (df["befrist"] == 1)].copy()
    if not befrist_spells.empty:
        befrist_duration = (
            befrist_spells.groupby("persnr")
            .apply(lambda x: (x["endepi"] - x["begepi"] + 1).sum())
            .reset_index(name="befrist_tot_dur")
        )
        df = df.merge(befrist_duration, on="persnr", how="left")
        df["befrist_tot_dur"] = df["befrist_tot_dur"].fillna(0)
    else:
        df["befrist_tot_dur"] = 0

    # Temporary agency work duration
    leih_spells = df[(df["behspell"]) & (df["leih"] == 1)].copy()
    if not leih_spells.empty:
        leih_duration = (
            leih_spells.groupby("persnr")
            .apply(lambda x: (x["endepi"] - x["begepi"] + 1).sum())
            .reset_index(name="leih_tot_dur")
        )
        df = df.merge(leih_duration, on="persnr", how="left")
        df["leih_tot_dur"] = df["leih_tot_dur"].fillna(0)
    else:
        df["leih_tot_dur"] = 0

    return df


def process_job_seeking(df):
    """Process job seeking history."""
    # Time since last job seeking episode
    seeking_spells = df[df["beg_ue"] == 1].copy()
    if not seeking_spells.empty:
        seeking_spells = seeking_spells.sort_values(
            ["persnr", "begepi"], ascending=[True, False]
        )
        last_seeking = seeking_spells.groupby("persnr").first().reset_index()

        # Calculate time since last seeking
        last_seeking["tsince_lastseeking"] = (
            last_seeking["beg_relevant_ue_date"] - last_seeking["endepi"] - 1
        )

        # Create categorical variable
        last_seeking["tsince_lastseeking_cat"] = 99999
        conditions = [
            (last_seeking["tsince_lastseeking"] <= 31),
            (last_seeking["tsince_lastseeking"] > 31)
            & (last_seeking["tsince_lastseeking"] <= 93),
            (last_seeking["tsince_lastseeking"] > 93)
            & (last_seeking["tsince_lastseeking"] <= 186),
            (last_seeking["tsince_lastseeking"] > 186)
            & (last_seeking["tsince_lastseeking"] <= 365),
            (last_seeking["tsince_lastseeking"] > 365)
            & (last_seeking["tsince_lastseeking"] <= 730),
            (last_seeking["tsince_lastseeking"] > 730)
            & (last_seeking["tsince_lastseeking"] <= 1825),
            (last_seeking["tsince_lastseeking"] > 1825),
        ]
        choices = [1, 2, 3, 4, 5, 6, 7]
        last_seeking["tsince_lastseeking_cat"] = np.select(
            conditions, choices, default=99999
        )

        # Calculate total seeking episodes and duration
        seeking_counts = (
            seeking_spells.groupby("persnr").size().reset_index(name="seeking1_total")
        )
        seeking_duration = (
            seeking_spells.groupby("persnr")["ue_duration"]
            .sum()
            .reset_index(name="seeking1_tot_dur")
        )

        # Merge with main dataframe
        df = df.merge(
            last_seeking[["persnr", "tsince_lastseeking", "tsince_lastseeking_cat"]],
            on="persnr",
            how="left",
        )
        df = df.merge(seeking_counts, on="persnr", how="left")
        df = df.merge(seeking_duration, on="persnr", how="left")

        # Calculate mean duration
        df["seeking1_m_dur"] = df["seeking1_tot_dur"] / df["seeking1_total"]

        # Fill missing values
        for col in ["seeking1_total", "seeking1_tot_dur", "seeking1_m_dur"]:
            df[col] = df[col].fillna(0)
    else:
        # Create empty variables if no seeking spells
        df["tsince_lastseeking"] = np.nan
        df["tsince_lastseeking_cat"] = 99999
        df["seeking1_total"] = 0
        df["seeking1_tot_dur"] = 0
        df["seeking1_m_dur"] = 0

    return df


def process_benefits(df):
    """Process benefit receipt history."""
    # Process LHG benefit receipt (ALG2)
    lhg_spells = df[df["lhgspell"]].copy()
    if not lhg_spells.empty:
        lhg_info = (
            lhg_spells.groupby("persnr")
            .agg(
                LHG_total=("anz_lst_lhg_kum", "max"),
                LHG_tot_dur=("tage_lst_lhg_kum", "max"),
            )
            .reset_index()
        )
        lhg_info["LHG_m_dur"] = lhg_info["LHG_tot_dur"] / lhg_info["LHG_total"]

        df = df.merge(lhg_info, on="persnr", how="left")
    else:
        df["LHG_total"] = 0
        df["LHG_tot_dur"] = 0
        df["LHG_m_dur"] = 0

    # Process LEH benefit receipt (ALG)
    leh_spells = df[df["lehspell"]].copy()
    if not leh_spells.empty:
        leh_info = (
            leh_spells.groupby("persnr")
            .agg(
                LEH_total=("anz_lst_leh_kum", "max"),
                LEH_tot_dur=("tage_lst_leh_kum", "max"),
            )
            .reset_index()
        )
        leh_info["LEH_m_dur"] = leh_info["LEH_tot_dur"] / leh_info["LEH_total"]

        df = df.merge(leh_info, on="persnr", how="left")
    else:
        df["LEH_total"] = 0
        df["LEH_tot_dur"] = 0
        df["LEH_m_dur"] = 0

    # Fill missing values
    for col in [
        "LHG_total",
        "LHG_tot_dur",
        "LHG_m_dur",
        "LEH_total",
        "LEH_tot_dur",
        "LEH_m_dur",
    ]:
        df[col] = df[col].fillna(0)

    return df


def process_almp_history(df):
    """Process ALMP (Active Labor Market Policy) history."""
    # Process ALMP measures
    mth_spells = df[df["mthspell"]].copy()
    if not mth_spells.empty:
        # Remove duplicates
        mth_spells = mth_spells.drop_duplicates(subset=["persnr", "begorig", "endorig"])

        # Calculate duration
        mth_spells["almp_dur"] = mth_spells["endorig"] - mth_spells["begorig"] + 1

        # Calculate overall ALMP statistics
        almp_counts = mth_spells.groupby("persnr").size().reset_index(name="almp_total")
        almp_duration = (
            mth_spells.groupby("persnr")["almp_dur"].agg(["sum", "mean"]).reset_index()
        )
        almp_duration.columns = ["persnr", "almp_tot_dur", "almp_m_dur"]

        # Calculate specialized ALMP statistics (Aktivierung und Weiterbildung)
        mth_spells["almp_aw"] = mth_spells["erwstat"] == 41
        aw_spells = mth_spells[mth_spells["almp_aw"]].copy()

        if not aw_spells.empty:
            aw_counts = (
                aw_spells.groupby("persnr").size().reset_index(name="almp_aw_total")
            )
            aw_duration = (
                aw_spells.groupby("persnr")["almp_dur"]
                .agg(["sum", "mean"])
                .reset_index()
            )
            aw_duration.columns = ["persnr", "almp_aw_tot_dur", "almp_aw_m_dur"]

            # Merge with main dataframe
            df = df.merge(almp_counts, on="persnr", how="left")
            df = df.merge(almp_duration, on="persnr", how="left")
            df = df.merge(aw_counts, on="persnr", how="left")
            df = df.merge(aw_duration, on="persnr", how="left")
        else:
            # Merge only general ALMP stats if no AW spells
            df = df.merge(almp_counts, on="persnr", how="left")
            df = df.merge(almp_duration, on="persnr", how="left")
            df["almp_aw_total"] = 0
            df["almp_aw_tot_dur"] = 0
            df["almp_aw_m_dur"] = 0
    else:
        # Create empty variables if no ALMP spells
        df["almp_total"] = 0
        df["almp_tot_dur"] = 0
        df["almp_m_dur"] = 0
        df["almp_aw_total"] = 0
        df["almp_aw_tot_dur"] = 0
        df["almp_aw_m_dur"] = 0

    # Process subsidized employment duration
    df["se_tot_dur"] = df.groupby("persnr")["tage_se_kum"].transform("max").fillna(0)

    return df


def process_biographical(df):
    """Process biographical variables."""
    # Process German citizenship
    df["german"] = df["deutsch"]
    df.loc[df["relevant_ue"] == 1 & df["german"].isna(), "german"] = 99999

    # Identify if citizenship changed to German
    citizenship_change = (
        df.groupby("persnr")
        .apply(
            lambda x: (x["deutsch"] == 1).any()
            and x.loc[x["deutsch"] == 1, "begepi"].min()
            != x.loc[x["deutsch"].notna(), "begepi"].min()
        )
        .reset_index(name="togerman")
    )

    df = df.merge(citizenship_change, on="persnr", how="left")
    df["togerman"] = df["togerman"].fillna(0)

    # Process place of residence (East/West Germany)
    df["wo_east"] = 99999
    df.loc[df["ao_region"] >= 11000, "wo_east"] = 1  # East Germany
    df.loc[(df["ao_region"] < 11000) & df["ao_region"].notna(), "wo_east"] = (
        0  # West Germany
    )

    # Process relocation information
    df["relocated"] = 99999
    relevant_ue = df["relevant_ue"] == 1
    df.loc[relevant_ue & (df["lastjob_ao_kreis"] != df["ao_region"]), "relocated"] = 1
    df.loc[relevant_ue & (df["lastjob_ao_kreis"] == df["ao_region"]), "relocated"] = 0

    # Calculate number of relocations
    locations = df[["persnr", "ao_region"]].drop_duplicates()
    move_counts = locations.groupby("persnr").size() - 1
    move_counts = move_counts.reset_index(name="moves")

    df = df.merge(move_counts, on="persnr", how="left")
    df["moves_noinfo"] = df["moves"].isna().astype(int)
    df["moves"] = df["moves"].fillna(0)

    # Adjust missings for biographical variables
    for col in ["ausbildung_imp", "relocated", "deutsch", "frau"]:
        df.loc[df[col].isna(), col] = 99999

    return df


if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
