"""
Feature Engineering

This file contains functions that generate new features for the SIAB dataset.
These functions will then be used to determine the difference in downstream
analyses when different data cleaning steps are applied.

Current feature engineering types include:
- Identification of long-term vs. short-term unemployment
- Generation of biographical variables (employment history, job history, etc.)
- Indexing of unemployment entries
- Reshaping data for machine learning models

Note from Zach Rewolinski:
'Judgment calls' are denoted by the comment "### JUDGMENT CALL". These are
data cleaning decisions that do not have a clear rationale and could be
debated/other actions could be taken. These are the decisions that we will want
to change later on to assess their impact on downstream analyses.
"""

# imports
import pandas as pd
import numpy as np


def identify_unemployment_episodes(df: pd.DataFrame,
                                   continuous_gap_threshold: int=42,
                                   ) -> pd.DataFrame:
    """
    Identifies unemployment episodes and classifies them as short-term or
    long-term. This function is based on Stata code provided by Hannah Mautner.

    The function processes SIAB data to identify job seeking spells, determine
    unemployment episode boundaries, calculate durations, and flag long-term
    unemployment (>= 365 days). It works with ASU/XASU spells for unemployment
    identification and BeH spells for employment exit detection.

    Args:
        df (pd.DataFrame): Dataset containing person-level spell data. Expected
            columns include: person_id, spell_count, episode_start_date,
            episode_end_date, spell_source, employment_status_group,
            and birth_year.

    Returns:
        pd.DataFrame: Dataset with added unemployment identification variables:
            year, age, seeking1, beg_ue, end_ue, beg_ue_date, end_ue_date,
            ue_duration, ltue, t_since_seeking, t_since_asu, next_employed_date,
            and t_till_emp.
    """

    # work on copy of dataframe
    df = df.copy()

    # calculate year and age
    if "episode_start_date" in df.columns:
        df["year"] = df["episode_start_date"].dt.year
    if "birth_year" in df.columns:
        df["age"] = df["year"] - df["birth_year"]

    ### JUDGMENT CALL
    # keep only MTH (spell_source == 4) and (X)ASU (spell_source == 5) spells
    ue_df = df[df["spell_source"].isin([4, 5])].copy()

    # step 1: identify job seeking during unemployment
    # add feature `seeking1`: (X)ASU spells with employment status `21` (job seeking while unemployed)
    ue_df["seeking1"] = (ue_df["spell_source"] == 5) & (
        ue_df["employment_status_group"] == 21
    )

    # keep only seeking1 spells
    ue_df = ue_df[ue_df["seeking1"] == 1].copy()

    # -------------------------------------------------------------------------
    # on this subset of spells, we compute:
    # - Time gaps between spells
    # - Whether spells are continuous (≤42 days apart)
    # - Episode boundaries (beg_ue, end_ue)
    # - Episode start/end dates
    # - Episode durations
    # -------------------------------------------------------------------------

    # sort by person and spell
    ue_df = ue_df.sort_values(["person_id", "spell_count"])

    # calculate time since last seeking episode
    # add feature `t_since_seeking`: time since last episode
    ue_df["t_since_seeking"] = ue_df["episode_start_date"] - ue_df.groupby("person_id")[
        "episode_end_date"
    ].shift(1)

    # calculate time since last ASU spell
    # add feature `t_since_asu`: time since last ASU spell
    ue_df["t_since_asu"] = ue_df["episode_start_date"] - ue_df.groupby("person_id")[
        "episode_end_date"
    ].shift(1)

    # JUDGMENT CALL: is there a reason it is gap <= 42 days in particular?
    #                 could we use a different threshold?
    # tag spells that are part of continuous job seeking episode
    # add feature `continuous`: spells that are part of continuous job seeking episode
    # (gap <= 42 days means continuous)
    ue_df["continuous"] = (ue_df["t_since_asu"] <= pd.Timedelta(days=continuous_gap_threshold)).astype(int)

    # step 2: identify separate unemployment episodes
    # 2.1 - begin of unemployment: every spell that is not continuous
    # add feature `beg_ue`: every spell that is not continuous
    ue_df["beg_ue"] = (ue_df["continuous"] != 1).astype(int)
    ue_df["beg_ue_date"] = np.where(
        ue_df["beg_ue"] == 1,
        ue_df["episode_start_date"],
        # using pd.NaT instead of np.nan for type consistency
        pd.NaT,
    )
    # ensure datetime dtype
    ue_df["beg_ue_date"] = pd.to_datetime(ue_df["beg_ue_date"])

    # copy begin date to all subsequent spells in same episode
    ue_df = ue_df.sort_values(["person_id", "spell_count"])
    ue_df["beg_ue_date"] = ue_df.groupby("person_id")["beg_ue_date"].ffill()

    # 2.2 - end of unemployment: spell before a new beginning
    # add feature `end_ue`: spell before a new beginning
    ue_df = ue_df.sort_values(["person_id", "spell_count"])
    ue_df["end_ue"] = (
        (ue_df.groupby("person_id")["beg_ue"].shift(-1) == 1)
        & (ue_df.groupby("person_id")["person_id"].shift(-1) == ue_df["person_id"])
    ).astype(int)

    # correction: last spell of each person is also an end
    ue_df["nrASU"] = ue_df.groupby("person_id").cumcount() + 1
    ue_df["NrASU"] = ue_df.groupby("person_id")["nrASU"].transform("max")
    ue_df.loc[ue_df["nrASU"] == ue_df["NrASU"], "end_ue"] = 1

    # date of end of unemployment
    ue_df["end_ue_date_help"] = np.where(
        ue_df["end_ue"] == 1,
        ue_df["episode_end_date"],
        # using pd.NaT instead of np.nan for type consistency
        pd.NaT,
    )
    # ensure datetime dtype
    ue_df["end_ue_date_help"] = pd.to_datetime(ue_df["end_ue_date_help"])
    ue_df["end_ue_date"] = ue_df.groupby(["person_id", "beg_ue_date"])[
        "end_ue_date_help"
    ].transform("max")

    # drop auxiliary variables
    ue_df = ue_df.drop(columns=["nrASU", "NrASU", "end_ue_date_help"])

    # step 3: calculate duration of unemployment
    # add feature `ue_duration`: duration of unemployment (in days)
    # calculate duration for all rows first, then filter
    ue_df["duration_help"] = (ue_df["episode_end_date"] - ue_df["beg_ue_date"]).dt.days
    ue_df.loc[ue_df["end_ue"] != 1, "duration_help"] = np.nan
    ue_df["ue_duration"] = ue_df.groupby(["person_id", "beg_ue_date"])[
        "duration_help"
    ].transform("max")
    ue_df = ue_df.drop(columns=["duration_help"])

    # -------------------------------------------------------------------------
    # We are done computing features for this subset and will now merge
    # back to the original dataset.
    # -------------------------------------------------------------------------

    # keep only necessary columns for merge
    ue_cols = [
        "person_id",
        "spell_count",
        "seeking1",
        "t_since_seeking",
        "t_since_asu",
        "beg_ue",
        "end_ue",
        "beg_ue_date",
        "end_ue_date",
        "ue_duration",
    ]
    ue_df = ue_df[ue_cols]

    # merge back to original dataset
    df = df.merge(ue_df, on=["person_id", "spell_count"], how="left")

    ### Note: not sure I understand the unemployment categories well enough to know if this is a reasonable approach.
    # step 4: find exits into employment using BeH spells
    # add feature `next_employed_date`: next employed date
    # add feature `t_till_emp`: time until employment
    # keep only BeH (spell_source == 1) and ASU (spell_source == 5) spells
    beh_asu_df = df[df["spell_source"].isin([1, 5])].copy()

    # drop ASU spells that don't mark end of unemployment
    beh_asu_df = beh_asu_df[
        ~((beh_asu_df["spell_source"] == 5) & (beh_asu_df["end_ue"] != 1))
    ]

    # sort by person, begin date, and source
    beh_asu_df = beh_asu_df.sort_values(
        ["person_id", "episode_start_date", "spell_source"]
    )

    # find next employment date (only standard social security employment, employment_status_group == 1)
    beh_asu_df["next_employed_date"] = np.where(
        (beh_asu_df["spell_source"] == 1)
        & (beh_asu_df["employment_status_group"] == 1),
        beh_asu_df["episode_start_date"],
        pd.NaT,  # using pd.NaT instead of np.nan for type consistency
    )
    # ensure datetime dtype
    beh_asu_df["next_employed_date"] = pd.to_datetime(beh_asu_df["next_employed_date"])

    # forward fill next employment date within person
    beh_asu_df["next_employed_date"] = beh_asu_df.groupby("person_id")[
        "next_employed_date"
    ].ffill()

    # calculate time until employment
    # add feature `t_till_emp`: time until employment
    # calculate for all rows first, then filter
    beh_asu_df["t_till_emp"] = (
        beh_asu_df["next_employed_date"]
        - beh_asu_df["episode_end_date"]
        - pd.Timedelta(days=1)
    )
    beh_asu_df.loc[beh_asu_df["end_ue"] != 1, "t_till_emp"] = pd.NaT

    # keep only end of unemployment spells
    exit_df = beh_asu_df[beh_asu_df["end_ue"] == 1][
        ["person_id", "spell_count", "next_employed_date", "t_till_emp"]
    ].copy()

    # merge back
    df = df.merge(exit_df, on=["person_id", "spell_count"], how="left")

    # copy to all spells of same unemployment episode
    df["next_employed_date_help"] = df["next_employed_date"]
    df["t_till_emp_help"] = df["t_till_emp"]

    df["next_employed_date"] = df.groupby(["person_id", "beg_ue_date"])[
        "next_employed_date_help"
    ].transform("max")
    df["t_till_emp"] = df.groupby(["person_id", "beg_ue_date"])[
        "t_till_emp_help"
    ].transform("max")

    df = df.drop(columns=["next_employed_date_help", "t_till_emp_help"])

    # step 5: flag long-term unemployment (>= 365 days)
    df["ltue"] = (df["ue_duration"] >= 365).astype(int)
    df.loc[df["ue_duration"].isna(), "ltue"] = np.nan

    # flag beginning of long-term unemployment
    df["beg_ltue"] = np.where((df["beg_ue"] == 1) & (df["ltue"] == 1), 1, np.nan)

    # copy unemployment episode dates to parallel spells
    df = df.sort_values(["person_id", "episode_start_date", "spell_source"])

    ### JUDGMENT CALL: could the missing values be handled differently?
    # forward fill beg_ue_date and end_ue_date within same episode
    df["beg_ue_date"] = df.groupby(["person_id", "episode_start_date"])[
        "beg_ue_date"
    ].ffill()
    df["end_ue_date"] = df.groupby(["person_id", "episode_start_date"])[
        "end_ue_date"
    ].ffill()
    df["ue_duration"] = df.groupby(["person_id", "episode_start_date"])[
        "ue_duration"
    ].ffill()

    # sort by person and spell
    df = df.sort_values(["person_id", "spell_count"])

    return df


def generate_biographical_variables(df: pd.DataFrame,
                                    new_job_notif_threshold: int=92,
                                    new_job_no_notif_threshold: int=366,
                                    separate_benefit_threshold: int=10,
                                    ) -> pd.DataFrame:
    """
    Generates biographical variables from longitudinal SIAB data. This function
    is based on Stata code provided by Johanna Eberle, Alexandra Schmucker,
    and Hannah Mautner.

    The function creates variables tracking employment history, job history,
    establishment history, benefit receipts, and subsidized employment. It
    handles vocational training, internships, and minijobs differently in
    different versions of employment variables.

    Args:
        df (pd.DataFrame): Dataset containing person-level spell data. Expected
            columns include: person_id, spell_count, episode_start_date,
            episode_end_date, observation_start_date, spell_source,
            employment_status_group, establishment_id, daily_wage, part_time,
            termination_reason_group, and other employment-related variables.

    Returns:
        pd.DataFrame: Dataset with added biographical variables including:
            employment start dates (start_employment1, start_employment2,
            start_employment3), employment durations (cum_days_emp1,
            cum_days_emp2, cum_days_emp3), establishment variables (first_day_estab,
            ndays_estab), job variables (ein_job, tage_job_kum, beg_job_sp),
            benefit variables (anz_lst_leh_kum, tage_lst_leh_kum, etc.),
            parallel jobs indicators, and subsidized employment duration.
    """

    # work on copy of dataframe
    df = df.copy()

    # observation counters
    df = df.sort_values(
        ["person_id", "episode_start_date", "spell_source", "spell_count"]
    )
    df["level1"] = df.groupby(
        ["person_id", "episode_start_date", "spell_source"]
    ).cumcount()
    df["level2"] = df.groupby(["person_id", "episode_start_date"]).cumcount()

    # tag vocational training, interns, and minijobs
    df["apprentice"] = (df["employment_status_group"] == 2).astype(int)
    df["intern"] = (df["employment_status_group"] == 5).astype(int)
    df["minijob"] = (df["employment_status_group"] == 3).astype(int)

    # employment person groups (5 categories)
    df["pg5"] = 5  # default: other
    df.loc[df["employment_status_group"] == 1, "pg5"] = 1  # standard employment
    df.loc[df["employment_status_group"] == 12, "pg5"] = 2  # apprentices
    df.loc[df["employment_status_group"] == 14, "pg5"] = 3  # part-time retirees
    df.loc[df["employment_status_group"] == 13, "pg5"] = 4  # mini-job

    ### JUDGMENT CALL: why are these our versions? for legal reasons?
    # version 1: employment without vocational training
    df["emp1"] = ((df["apprentice"] != 1) & (df["spell_source"] == 1)).astype(int)

    # first day in employment (version 1)
    # add feature `start_employment1`: first day in employment (w/o voc. training)
    emp1_df = df[df["emp1"] == 1].copy()
    if len(emp1_df) > 0:
        start_employment1 = emp1_df.groupby("person_id")["observation_start_date"].min()
        df = df.merge(
            start_employment1.to_frame("start_employment1"),
            left_on="person_id",
            right_index=True,
            how="left",
        )
    else:
        df["start_employment1"] = np.nan

    # version 2: without vocational training and internships
    df["emp2"] = (
        (df["apprentice"] != 1) & (df["intern"] != 1) & (df["spell_source"] == 1)
    ).astype(int)

    # add feature `start_employment2`: first day in employment (w/o voc. training, internships)
    emp2_df = df[df["emp2"] == 1].copy()
    if len(emp2_df) > 0:
        start_employment2 = emp2_df.groupby("person_id")["observation_start_date"].min()
        df = df.merge(
            start_employment2.to_frame("start_employment2"),
            left_on="person_id",
            right_index=True,
            how="left",
        )
    else:
        df["start_employment2"] = np.nan

    # version 3: without vocational training, internships, and minijobs
    df["emp3"] = (
        (df["apprentice"] != 1)
        & (df["intern"] != 1)
        & (df["minijob"] != 1)
        & (df["spell_source"] == 1)
    ).astype(int)

    # add feature `start_employment3`: first day in employment (w/o voc. training, internships, minijobs)
    emp3_df = df[df["emp3"] == 1].copy()
    if len(emp3_df) > 0:
        start_employment3 = emp3_df.groupby("person_id")["observation_start_date"].min()
        df = df.merge(
            start_employment3.to_frame("start_employment3"),
            left_on="person_id",
            right_index=True,
            how="left",
        )
    else:
        df["start_employment3"] = np.nan

    # number of days in employment (running totals)
    df = df.sort_values(["person_id", "episode_start_date", "spell_count"])

    # version 1
    # add feature `cum_days_emp1`: cumulative days in employment (w/o voc. training)
    emp1_spells = df[df["emp1"] == 1].copy()
    if len(emp1_spells) > 0:
        emp1_spells["d1"] = (
            emp1_spells["episode_end_date"]
            - emp1_spells["episode_start_date"]
            + pd.Timedelta(days=1)
        ).dt.days
        emp1_spells["cum_days_emp1"] = emp1_spells.groupby("person_id")["d1"].cumsum()
        cum_days_emp1_max = (
            emp1_spells.groupby("person_id")["cum_days_emp1"]
            .max()
            .to_frame("cum_days_emp1")
        )
        df = df.merge(
            cum_days_emp1_max, left_on="person_id", right_index=True, how="left"
        )
    else:
        df["cum_days_emp1"] = 0

    # version 2
    # add feature `cum_days_emp2`: cumulative days in employment (w/o voc. training, internships)
    emp2_spells = df[(df["emp2"] == 1) & (df["intern"] != 1)].copy()
    if len(emp2_spells) > 0:
        emp2_spells["d2"] = (
            emp2_spells["episode_end_date"]
            - emp2_spells["episode_start_date"]
            + pd.Timedelta(days=1)
        ).dt.days
        emp2_spells["cum_days_emp2"] = emp2_spells.groupby("person_id")["d2"].cumsum()
        cum_days_emp2_max = (
            emp2_spells.groupby("person_id")["cum_days_emp2"]
            .max()
            .to_frame("cum_days_emp2")
        )
        df = df.merge(
            cum_days_emp2_max, left_on="person_id", right_index=True, how="left"
        )
    else:
        df["cum_days_emp2"] = 0

    # version 3
    # add feature `cum_days_emp3`: cumulative days in employment (w/o voc. training, internships, minijobs)
    emp3_spells = df[
        (df["emp3"] == 1) & (df["intern"] != 1) & (df["minijob"] != 1)
    ].copy()
    if len(emp3_spells) > 0:
        emp3_spells["d3"] = (
            emp3_spells["episode_end_date"]
            - emp3_spells["episode_start_date"]
            + pd.Timedelta(days=1)
        ).dt.days
        emp3_spells["cum_days_emp3"] = emp3_spells.groupby("person_id")["d3"].cumsum()
        cum_days_emp3_max = (
            emp3_spells.groupby("person_id")["cum_days_emp3"]
            .max()
            .to_frame("cum_days_emp3")
        )
        df = df.merge(
            cum_days_emp3_max, left_on="person_id", right_index=True, how="left"
        )
    else:
        df["cum_days_emp3"] = 0

    # parallel jobs (in different establishments)
    # add feature `morethanonejob`: indicator for parallel jobs in different establishments
    # add feature `ndays_morethanonejob`: cumulative days with more than one job
    beh_df = df[df["spell_source"] == 1].copy()
    if len(beh_df) > 0:
        beh_df["tentgelt_h"] = -beh_df["daily_wage"]
        beh_df = beh_df.sort_values(
            ["person_id", "episode_start_date", "establishment_id", "tentgelt_h"]
        )
        beh_df["nrSE"] = (
            beh_df.groupby(
                ["person_id", "episode_start_date", "establishment_id", "tentgelt_h"]
            ).cumcount()
            + 1
        )

        beh_df["nrE"] = np.where(
            beh_df["nrSE"] == 1,
            beh_df.groupby(["person_id", "episode_start_date"]).cumcount() + 1,
            np.nan,
        )
        beh_df["nr_jobs"] = np.where(
            beh_df["nrSE"] == 1,
            beh_df.groupby(["person_id", "episode_start_date"])["nrSE"].transform(
                "count"
            ),
            np.nan,
        )

        beh_df["morethanonejob"] = (beh_df["nr_jobs"] > 1).astype(float)
        beh_df["morethanonejob"] = beh_df.groupby(["person_id", "episode_start_date"])[
            "morethanonejob"
        ].ffill()

        # duration with more than one job
        beh_df["d"] = np.where(
            (beh_df["nrSE"] == 1)
            & (beh_df["nrE"] == 1)
            & (beh_df["morethanonejob"] == 1),
            (
                beh_df["episode_end_date"]
                - beh_df["episode_start_date"]
                + pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )
        beh_df["ndays_morethanonejob"] = beh_df.groupby("person_id")["d"].cumsum()

        morethanonejob_cols = [
            "person_id",
            "spell_count",
            "morethanonejob",
            "ndays_morethanonejob",
        ]
        df = df.merge(
            beh_df[morethanonejob_cols], on=["person_id", "spell_count"], how="left"
        )
    else:
        df["morethanonejob"] = np.nan
        df["ndays_morethanonejob"] = np.nan

    # first day in establishment
    # add feature `first_day_estab`: first day in establishment
    if "establishment_id" in df.columns:
        first_day_estab = (
            df[df["establishment_id"].notna()]
            .groupby(["person_id", "establishment_id"])["episode_start_date"]
            .min()
        )
        first_day_estab = (
            first_day_estab.groupby("person_id").min().to_frame("first_day_estab")
        )
        df = df.merge(
            first_day_estab, left_on="person_id", right_index=True, how="left"
        )
    else:
        df["first_day_estab"] = np.nan

    # number of days in establishment
    # add feature `ndays_estab`: cumulative days in establishment
    if "establishment_id" in df.columns:
        bet_df = df[df["establishment_id"].notna()].copy()
        bet_df = bet_df.sort_values(
            [
                "person_id",
                "establishment_id",
                "episode_start_date",
                "episode_end_date",
                "spell_count",
            ]
        )
        bet_df["nrB"] = (
            bet_df.groupby(
                [
                    "person_id",
                    "establishment_id",
                    "episode_start_date",
                    "episode_end_date",
                ]
            ).cumcount()
            + 1
        )
        bet_df["dauer"] = np.where(
            bet_df["nrB"] == 1,
            (
                bet_df["episode_end_date"]
                - bet_df["episode_start_date"]
                + pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )
        bet_df["ndays_estab"] = bet_df.groupby(["person_id", "establishment_id"])[
            "dauer"
        ].cumsum()
        ndays_estab_max = (
            bet_df.groupby(["person_id", "establishment_id"])["ndays_estab"]
            .max()
            .groupby("person_id")
            .max()
            .to_frame("ndays_estab")
        )
        df = df.merge(
            ndays_estab_max, left_on="person_id", right_index=True, how="left"
        )
    else:
        df["ndays_estab"] = np.nan

    # first day in job and number of days in job
    # add feature `first_day_job`: first day in job
    # add feature `tage_job_kum`: cumulative days in job
    # add feature `beg_job_sp`: indicator for start of new job
    if "establishment_id" in df.columns:
        job_df = df[df["establishment_id"].notna()].copy()
        job_df = job_df.sort_values(
            ["person_id", "apprentice", "establishment_id", "spell_count"]
        )

        # mark subsequent episodes of same job
        job_df["job"] = (
            (job_df["person_id"] == job_df["person_id"].shift(1))
            & (job_df["establishment_id"] == job_df["establishment_id"].shift(1))
            & (job_df["apprentice"] == job_df["apprentice"].shift(1))
        ).astype(int)

        # consider ending notification and gaps
        # check for termination_reason_group or grund
        termination_col = None
        for col in ["termination_reason_group", "grund_gr", "grund"]:
            if col in job_df.columns:
                termination_col = col
                break

        if termination_col is not None:
            job_df["end"] = job_df.groupby(
                ["person_id", "apprentice", "establishment_id", "episode_start_date"]
            )[termination_col].transform(lambda x: x.iloc[0] if len(x) > 0 else np.nan)
            job_df["end"] = job_df["end"].isin([0, 5]).astype(int)
        else:
            job_df["end"] = 0

        job_df["gap"] = np.where(
            job_df["job"] == 1,
            (
                job_df["episode_start_date"]
                - job_df["episode_end_date"].shift(1)
                - pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )

        ### JUDGMENT CALL: thresholds for counting as new job (92 days, 366 days)
        # count as new job if gap > 92 days with end notification, or gap > 366 days
        job_df.loc[(job_df["end"].shift(1) == 1) & (job_df["gap"] > new_job_notif_threshold), "job"] = np.nan
        job_df.loc[job_df["gap"] > new_job_no_notif_threshold, "job"] = np.nan

        # generate start date of job
        job_df["ein_job"] = job_df["episode_start_date"]
        job_df.loc[job_df["job"] == 1, "ein_job"] = job_df.loc[
            job_df["job"] == 1, "ein_job"
        ].shift(1)

        # number of days in job
        job_df["nrA"] = (
            job_df.groupby(
                ["person_id", "apprentice", "establishment_id", "episode_start_date"]
            ).cumcount()
            + 1
        )
        job_df["jobdauer"] = (
            job_df["episode_end_date"]
            - job_df["episode_start_date"]
            + pd.Timedelta(days=1)
        ).dt.days
        job_df["jobdauer_kum"] = job_df["jobdauer"]
        job_df["jobdauer_dup"] = np.where(job_df["nrA"] != 1, job_df["jobdauer"], 0)

        job_df.loc[job_df["job"] == 1, "jobdauer_kum"] = (
            job_df.loc[job_df["job"] == 1, "jobdauer_kum"].shift(1)
            + job_df.loc[job_df["job"] == 1, "jobdauer"]
            - job_df.loc[job_df["job"] == 1, "jobdauer_dup"]
        )

        job_df["job_start"] = np.where(
            (job_df["job"].isna()) & (job_df["spell_source"] == 1), 1, 0
        )
        job_df["tage_job"] = job_df["jobdauer_kum"]

        job_cols = ["person_id", "spell_count", "ein_job", "tage_job", "job_start"]
        df = df.merge(job_df[job_cols], on=["person_id", "spell_count"], how="left")
    else:
        df["ein_job"] = np.nan
        df["tage_job"] = np.nan
        df["job_start"] = 0

    # benefit receipts (LeH and LHG)
    # LeH benefits (spell_source == 2)
    # add feature `anz_lst_leh_kum`: cumulative count of LeH benefit receipts
    # add feature `tage_lst_leh_kum`: cumulative days receiving LeH benefits
    df["quelleLeH"] = (df["spell_source"] == 2).astype(int)
    leh_df = df[df["quelleLeH"] == 1].copy()
    if len(leh_df) > 0:
        leh_df = leh_df.sort_values(
            ["person_id", "episode_start_date", "spell_source", "spell_count"]
        )
        leh_df["nrLeH"] = (
            leh_df.groupby(["person_id", "episode_start_date", "quelleLeH"]).cumcount()
            + 1
        )

        leh_df["ende_vor_leh"] = leh_df.groupby("person_id")["episode_end_date"].shift(
            1
        )
        leh_df["ende_vor_leh"] = leh_df.groupby("person_id")["ende_vor_leh"].ffill()

        ### JUDGMENT CALL: gap threshold for counting as separate benefit receipt (10 days)
        leh_df["lst_leh"] = (
            (leh_df["quelleLeH"] == 1)
            & (leh_df["nrLeH"] == 1)
            & (
                (leh_df["episode_start_date"] - leh_df["ende_vor_leh"])
                > pd.Timedelta(days=separate_benefit_threshold)
            )
        ).astype(int)

        leh_df = leh_df.sort_values(
            ["person_id", "episode_start_date", "lst_leh"],
            ascending=[True, True, False],
        )
        leh_df["anz_lst_leh"] = leh_df.groupby("person_id")["lst_leh"].cumsum()

        leh_df["breceipt_leh"] = 1
        leh_df = leh_df.sort_values(
            ["person_id", "episode_start_date", "quelleLeH"],
            ascending=[True, True, False],
        )
        leh_df["breceipt_leh"] = leh_df.groupby(["person_id", "episode_start_date"])[
            "breceipt_leh"
        ].ffill()

        # duration of LeH benefits
        leh_df["lstdauer_leh"] = np.where(
            (leh_df["quelleLeH"] == 1) & (leh_df["nrLeH"] == 1),
            (
                leh_df["episode_end_date"]
                - leh_df["episode_start_date"]
                + pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )
        leh_df["tage_lst_leh"] = leh_df.groupby("person_id")["lstdauer_leh"].cumsum()
        leh_df["tage_lst_leh"] = leh_df.groupby(["person_id", "episode_start_date"])[
            "tage_lst_leh"
        ].transform("first")

        leh_cols = [
            "person_id",
            "spell_count",
            "anz_lst_leh",
            "beg_lst_leh_sp",
            "lst_leh",
            "tage_lst_leh",
            "tage_lst_leh_sp",
            "tage_lst_leh_ep",
        ]
        leh_df["beg_lst_leh_sp"] = leh_df["lst_leh"]
        leh_df["tage_lst_leh_sp"] = leh_df["lstdauer_leh"]
        leh_df["tage_lst_leh_ep"] = leh_df.groupby(["person_id", "anz_lst_leh"])[
            "lstdauer_leh"
        ].transform("sum")

        df = df.merge(leh_df[leh_cols], on=["person_id", "spell_count"], how="left")
    else:
        for col in [
            "anz_lst_leh",
            "beg_lst_leh_sp",
            "lst_leh",
            "tage_lst_leh",
            "tage_lst_leh_sp",
            "tage_lst_leh_ep",
        ]:
            df[col] = 0

    # similar process for LHG benefits (spell_source == 3)
    # add feature `anz_lst_lhg_kum`: cumulative count of LHG benefit receipts
    # add feature `tage_lst_lhg_kum`: cumulative days receiving LHG benefits
    df["quelleLHG"] = (df["spell_source"] == 3).astype(int)
    lhg_df = df[df["quelleLHG"] == 1].copy()
    if len(lhg_df) > 0:
        lhg_df = lhg_df.sort_values(
            ["person_id", "episode_start_date", "spell_source", "spell_count"]
        )
        lhg_df["nrLHG"] = (
            lhg_df.groupby(["person_id", "episode_start_date", "quelleLHG"]).cumcount()
            + 1
        )

        lhg_df["ende_vor_lhg"] = lhg_df.groupby("person_id")["episode_end_date"].shift(
            1
        )
        lhg_df["ende_vor_lhg"] = lhg_df.groupby("person_id")["ende_vor_lhg"].ffill()

        ### JUDGMENT CALL: gap threshold for counting as separate benefit receipt (10 days)
        lhg_df["lst_lhg"] = (
            (lhg_df["quelleLHG"] == 1)
            & (lhg_df["nrLHG"] == 1)
            & (
                (lhg_df["episode_start_date"] - lhg_df["ende_vor_lhg"])
                > pd.Timedelta(days=separate_benefit_threshold)
            )
        ).astype(int)

        lhg_df = lhg_df.sort_values(
            ["person_id", "episode_start_date", "lst_lhg"],
            ascending=[True, True, False],
        )
        lhg_df["anz_lst_lhg"] = lhg_df.groupby("person_id")["lst_lhg"].cumsum()

        lhg_df["breceipt_lhg"] = 1
        lhg_df = lhg_df.sort_values(
            ["person_id", "episode_start_date", "quelleLHG"],
            ascending=[True, True, False],
        )
        lhg_df["breceipt_lhg"] = lhg_df.groupby(["person_id", "episode_start_date"])[
            "breceipt_lhg"
        ].ffill()

        lhg_df["lstdauer_lhg"] = np.where(
            (lhg_df["quelleLHG"] == 1) & (lhg_df["nrLHG"] == 1),
            (
                lhg_df["episode_end_date"]
                - lhg_df["episode_start_date"]
                + pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )
        lhg_df["tage_lst_lhg"] = lhg_df.groupby("person_id")["lstdauer_lhg"].cumsum()
        lhg_df["tage_lst_lhg"] = lhg_df.groupby(["person_id", "episode_start_date"])[
            "tage_lst_lhg"
        ].transform("first")

        lhg_cols = [
            "person_id",
            "spell_count",
            "anz_lst_lhg",
            "beg_lst_lhg_sp",
            "lst_lhg",
            "tage_lst_lhg",
            "tage_lst_lhg_sp",
            "tage_lst_lhg_ep",
        ]
        lhg_df["beg_lst_lhg_sp"] = lhg_df["lst_lhg"]
        lhg_df["tage_lst_lhg_sp"] = lhg_df["lstdauer_lhg"]
        lhg_df["tage_lst_lhg_ep"] = lhg_df.groupby(["person_id", "anz_lst_lhg"])[
            "lstdauer_lhg"
        ].transform("sum")

        df = df.merge(lhg_df[lhg_cols], on=["person_id", "spell_count"], how="left")
    else:
        for col in [
            "anz_lst_lhg",
            "beg_lst_lhg_sp",
            "lst_lhg",
            "tage_lst_lhg",
            "tage_lst_lhg_sp",
            "tage_lst_lhg_ep",
        ]:
            df[col] = 0

    # subsidized employment duration
    # add feature `se_ep`: indicator for subsidized employment episode
    # add feature `tage_se_kum`: cumulative days in subsidized employment
    df["se"] = (
        (df["spell_source"] == 4) & (df["employment_status_group"].isin([41, 44]))
    ).astype(int)
    df = df.sort_values(
        ["person_id", "episode_start_date", "spell_source"],
        ascending=[True, True, False],
    )
    df["se"] = df.groupby(["person_id", "episode_start_date"])["se"].ffill()

    se_df = df[
        (df["spell_source"] == 4) & (df["employment_status_group"].isin([41, 44]))
    ].copy()
    if len(se_df) > 0:
        se_df["quelleMSE"] = 1
        se_df["nrMSE"] = (
            se_df.groupby(["person_id", "episode_start_date", "quelleMSE"]).cumcount()
            + 1
        )
        se_df["sedauer"] = np.where(
            se_df["nrMSE"] == 1,
            (
                se_df["episode_end_date"]
                - se_df["episode_start_date"]
                + pd.Timedelta(days=1)
            ).dt.days,
            np.nan,
        )
        se_df["tage_se"] = se_df.groupby("person_id")["sedauer"].cumsum()
        se_df["tage_se"] = se_df.groupby(["person_id", "episode_start_date"])[
            "tage_se"
        ].ffill()

        tage_se_max = se_df.groupby("person_id")["tage_se"].max().to_frame("tage_se")
        df = df.merge(tage_se_max, left_on="person_id", right_index=True, how="left")
    else:
        df["tage_se"] = 0

    # adjust missing values for establishment/job variables
    ### JUDGMENT CALL: should these variables be set to NaN for non-employment spells?
    for var in ["first_day_estab", "ndays_estab", "ein_job", "tage_job"]:
        if var in df.columns:
            df.loc[df["spell_source"] != 1, var] = np.nan

    # sort by person and spell
    df = df.sort_values(["person_id", "spell_count"])

    return df


def generate_employment_history(df: pd.DataFrame, entry_number: int) -> pd.DataFrame:
    """
    Generates employment history variables for a specific unemployment entry.
    This function is based on Stata code provided by Hannah Mautner.

    The function derives status-before indicators, job and establishment counts,
    cumulative employment durations, last job characteristics, and time-since
    measures for each unemployment entry. It processes spells up to the relevant
    unemployment episode and aggregates information required for downstream
    analysis.

    Args:
        df (pd.DataFrame): Dataset containing employment and unemployment
            spells. Expected columns include person_id, spell_source,
            episode_start_date, episode_end_date, beg_ue_date, nrEntry, and
            previously engineered job history variables.
        entry_number (int): Unemployment entry number (1-15) being processed.

    Returns:
        pd.DataFrame: Dataset with added employment history variables.
    """

    df = df.copy()

    # align column names if only German variants exist
    column_aliases = {
        "person_id": ["persnr"],
        "episode_start_date": ["begepi"],
        "episode_end_date": ["endepi"],
        "spell_source": ["quelle_gr"],
        "establishment_id": ["bnn"],
        "employment_status_group": ["erwstat"],
        "apprentice": ["azubi"],
        "industry_destatis": ["indust"],
        "district_region": ["ao_region"],
        "temporary_employment": ["leih"],
        "fixed_term_employment": ["befrist"],
        "part_time": ["teilzeit"],
        "education_level_imputed": ["ausbildung_imp"],
        "daily_wage": ["tentgelt"],
        "start_employment1": ["ein_erw1"],
        "cum_days_emp1": ["tage_erw1_kum"],
        "cum_days_emp2": ["tage_erw2_kum"],
        "cum_days_emp3": ["tage_erw3_kum"],
        "tage_job": ["tage_job_kum"],
    }
    for english, candidates in column_aliases.items():
        if english not in df.columns:
            for candidate in candidates:
                if candidate in df.columns:
                    df[english] = df[candidate]
                    break

    # ensure necessary date columns are datetime
    date_columns = [
        "beg_ue_date",
        "episode_start_date",
        "episode_end_date",
        "start_employment1",
        "lm_contact_date",
        "ft_lm_contact_date",
    ]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    # identify relevant unemployment entry
    df["relevant_ue"] = np.where(df["nrEntry"] == entry_number, 1, np.nan)
    df["ue_pop"] = df.groupby("person_id")["relevant_ue"].transform("max")
    df = df[df["ue_pop"] == 1].copy()

    # begin date of relevant unemployment episode
    df["date_help"] = np.where(df["relevant_ue"] == 1, df["beg_ue_date"], pd.NaT)
    df["date_help"] = pd.to_datetime(df["date_help"])
    df["beg_relevant_ue_date"] = df.groupby("person_id")["date_help"].transform("max")
    df["beg_relevant_ue_date"] = pd.to_datetime(df["beg_relevant_ue_date"])

    # keep spells up to the start of relevant unemployment episode
    df = df[df["episode_start_date"] <= df["beg_relevant_ue_date"]].copy()

    # spell type indicators
    df["lhgspell"] = (df["spell_source"] == 3).astype(int)
    df["behspell"] = (df["spell_source"] == 1).astype(int)
    df["lehspell"] = (df["spell_source"] == 2).astype(int)
    df["asuspell"] = (df["spell_source"] == 5).astype(int)
    df["mthspell"] = (df["spell_source"] == 4).astype(int)

    # status before unemployment (within 42 days)
    before_df = df[df["episode_start_date"] < df["beg_relevant_ue_date"]].copy()
    if len(before_df) > 0:
        before_df = before_df.sort_values(["person_id", "episode_start_date"])
        before_df["status_beg_date"] = before_df.groupby("person_id")[
            "episode_start_date"
        ].transform("max")
        before_df = before_df[
            before_df["episode_start_date"] == before_df["status_beg_date"]
        ].copy()

        before_df["episode_end_date"] = pd.to_datetime(before_df["episode_end_date"])
        before_df["t_since_spell"] = (
            before_df["beg_relevant_ue_date"]
            - before_df["episode_end_date"]
            + pd.Timedelta(days=1)
        ).dt.days

        before_df["employed"] = np.where(
            before_df["t_since_spell"] <= 42,
            before_df.groupby("person_id")["behspell"].transform("max"),
            0,
        )
        before_df["receipt_leh"] = np.where(
            before_df["t_since_spell"] <= 42,
            before_df.groupby("person_id")["lehspell"].transform("max"),
            0,
        )
        before_df["receipt_lhg"] = np.where(
            before_df["t_since_spell"] <= 42,
            before_df.groupby("person_id")["lhgspell"].transform("max"),
            0,
        )
        if "se_ep" in before_df.columns:
            before_df["se"] = np.where(
                before_df["t_since_spell"] <= 42,
                before_df.groupby("person_id")["se_ep"].transform("max"),
                0,
            )
        else:
            before_df["se"] = 0

        before_df["employment_status_group"] = before_df[
            "employment_status_group"
        ].fillna(-1)
        before_df["ASU_notue_seeking_help"] = (
            before_df["employment_status_group"] == 23
        ).astype(int)
        before_df["ASU_notue_seeking"] = np.where(
            before_df["t_since_spell"] <= 42,
            before_df.groupby("person_id")["ASU_notue_seeking_help"].transform("max"),
            0,
        )
        before_df["ASU_other_help"] = np.where(
            before_df["t_since_spell"] <= 42,
            before_df.groupby("person_id")["asuspell"].transform("max"),
            0,
        )
        before_df["ASU_other"] = np.where(
            (before_df["ASU_other_help"] == 1) & (before_df["ASU_notue_seeking"] != 1),
            1,
            0,
        )
        before_df["break"] = (before_df["t_since_spell"] > 42).astype(int)

        before_summary = before_df.groupby("person_id").first().reset_index()
        before_cols = [
            "person_id",
            "employed",
            "receipt_leh",
            "receipt_lhg",
            "se",
            "ASU_notue_seeking",
            "ASU_other",
            "break",
        ]
        before_summary = before_summary[["person_id"] + before_cols[1:]]
        before_summary.columns = ["person_id"] + [
            f"{col}_before" for col in before_cols[1:]
        ]
        df = df.merge(before_summary, on="person_id", how="left")

        for col in [
            "employed_before",
            "receipt_leh_before",
            "receipt_lhg_before",
            "se_before",
            "ASU_notue_seeking_before",
            "ASU_other_before",
        ]:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        if "break_before" in df.columns:
            df["break_before"] = df["break_before"].fillna(1)
    else:
        for col in [
            "employed_before",
            "receipt_leh_before",
            "receipt_lhg_before",
            "se_before",
            "ASU_notue_seeking_before",
            "ASU_other_before",
        ]:
            df[col] = 0
        df["break_before"] = 1

    # number of different jobs and establishments
    jobs_df = df[
        (df["episode_start_date"] < df["beg_relevant_ue_date"])
        & (df["spell_source"] == 1)
    ].copy()

    if len(jobs_df) > 0 and "ein_job" in jobs_df.columns:
        jobs_df = jobs_df.sort_values(
            ["person_id", "ein_job", "establishment_id", "episode_start_date"]
        )
        jobs_df["nrE"] = (
            jobs_df.groupby(["person_id", "ein_job", "establishment_id"]).cumcount() + 1
        )
        jobs_df = jobs_df[jobs_df["nrE"] == 1].copy()
        jobs_df["emp_total"] = jobs_df.groupby("person_id")["person_id"].transform(
            "count"
        )

        if "establishment_id" in jobs_df.columns:
            jobs_df = jobs_df.sort_values(["person_id", "establishment_id"])
            jobs_df["nrEst"] = jobs_df.groupby("person_id").cumcount() + 1
            jobs_df["est_total"] = np.where(
                jobs_df["nrEst"] == 1,
                jobs_df.groupby("person_id")["nrEst"].transform("max"),
                np.nan,
            )
            jobs_df = jobs_df[jobs_df["nrEst"] == 1].copy()

        jobs_df_no_voc = (
            jobs_df[jobs_df["apprentice"] != 1].copy()
            if "apprentice" in jobs_df.columns
            else jobs_df.copy()
        )
        if len(jobs_df_no_voc) > 0:
            jobs_df_no_voc = jobs_df_no_voc.sort_values(
                ["person_id", "ein_job", "establishment_id", "episode_start_date"]
            )
            jobs_df_no_voc["nrE1"] = (
                jobs_df_no_voc.groupby(
                    ["person_id", "ein_job", "establishment_id"]
                ).cumcount()
                + 1
            )
            jobs_df_no_voc = jobs_df_no_voc[jobs_df_no_voc["nrE1"] == 1].copy()
            jobs_df_no_voc["emp1_total"] = jobs_df_no_voc.groupby("person_id")[
                "person_id"
            ].transform("count")
        else:
            jobs_df_no_voc = pd.DataFrame(columns=["person_id", "emp1_total"])

        jobs_summary = jobs_df.groupby("person_id", as_index=False).first()
        keep_cols = ["person_id"] + [
            col for col in ["est_total", "emp_total"] if col in jobs_summary.columns
        ]
        jobs_summary = jobs_summary[keep_cols]
        emp1_summary = jobs_df_no_voc[["person_id", "emp1_total"]].drop_duplicates(
            subset="person_id", keep="first"
        )
        jobs_summary = jobs_summary.merge(emp1_summary, on="person_id", how="left")
        df = df.merge(jobs_summary, on="person_id", how="left")

        for col in ["est_total", "emp_total", "emp1_total"]:
            if col in df.columns:
                df[col] = df[col].fillna(0)
    else:
        for col in ["est_total", "emp_total", "emp1_total"]:
            df[col] = 0

    # main industry and durations by industry
    job_duration_col = None
    if "tage_job" in df.columns:
        job_duration_col = "tage_job"
    elif "tage_job_kum" in df.columns:
        job_duration_col = "tage_job_kum"

    if (
        "industry_destatis" in df.columns
        and "ein_job" in df.columns
        and job_duration_col is not None
    ):
        industry_df = df[
            (df["episode_start_date"] < df["beg_relevant_ue_date"])
            & (df["beg_job_sp"] == 1)
        ].copy()

        if len(industry_df) > 0:
            industry_df["job_duration_help"] = industry_df.groupby(
                ["person_id", "industry_destatis", "ein_job"]
            )[job_duration_col].transform("max")
            industry_df["job_duration_help2"] = industry_df.groupby(
                ["person_id", "industry_destatis"]
            )["job_duration_help"].transform("sum")
            industry_df["industry_tot_dur"] = industry_df.groupby(
                ["person_id", "industry_destatis"]
            )["job_duration_help2"].transform("max")
            industry_df["main_industry_help"] = industry_df.groupby("person_id")[
                "industry_tot_dur"
            ].transform("max")
            industry_df["main_industry_help2"] = np.where(
                industry_df["industry_tot_dur"] == industry_df["main_industry_help"],
                industry_df["industry_destatis"],
                np.nan,
            )
            industry_df["main_industry"] = industry_df.groupby("person_id")[
                "main_industry_help2"
            ].transform("max")

            for i in range(1, 15):
                col_name = f"industry1_destatis_tot_dur_{i}"
                industry_df[col_name] = np.where(
                    industry_df["industry_destatis"] == i,
                    industry_df["industry_tot_dur"],
                    np.nan,
                )
                industry_df[col_name] = industry_df.groupby("person_id")[
                    col_name
                ].transform("max")

            industry_summary = (
                industry_df.groupby("person_id")
                .first()[
                    ["main_industry"]
                    + [f"industry1_destatis_tot_dur_{i}" for i in range(1, 15)]
                ]
                .reset_index()
            )
            df = df.merge(industry_summary, on="person_id", how="left")

            for i in range(1, 15):
                col_name = f"industry1_destatis_tot_dur_{i}"
                if col_name in df.columns:
                    df[col_name] = df[col_name].fillna(0)
            df["main_industry"] = df["main_industry"].fillna(99999)
        else:
            df["main_industry"] = 99999
            for i in range(1, 15):
                df[f"industry1_destatis_tot_dur_{i}"] = 0

    # cumulative employment duration
    emp_dur_df = df[df["episode_start_date"] < df["beg_relevant_ue_date"]].copy()
    if len(emp_dur_df) > 0:
        duration_map = {
            "cum_days_emp1": "emp1_total_dur",
            "cum_days_emp2": "emp2_total_dur",
            "cum_days_emp3": "emp3_total_dur",
        }
        for source_col, target_col in duration_map.items():
            if source_col in emp_dur_df.columns:
                helper_col = f"{source_col}_help"
                emp_dur_df[helper_col] = emp_dur_df.groupby("person_id")[
                    source_col
                ].transform("max")
                emp_dur_max = (
                    emp_dur_df.groupby("person_id").first()[[helper_col]].reset_index()
                )
                emp_dur_max.columns = ["person_id", target_col]
                df = df.merge(emp_dur_max, on="person_id", how="left")

        if "emp1_total_dur" in df.columns and "emp1_total" in df.columns:
            df["emp1_m_dur"] = df["emp1_total_dur"] / df["emp1_total"].replace(
                0, np.nan
            )
            df["emp1_m_dur"] = df["emp1_m_dur"].fillna(0)

    # time since first employment
    employment_start_col = None
    if "start_employment1" in df.columns:
        employment_start_col = "start_employment1"
    elif "ein_erw1" in df.columns:
        employment_start_col = "ein_erw1"

    if employment_start_col is not None:
        df[employment_start_col] = pd.to_datetime(df[employment_start_col])
        df["tsince_ein_erw1"] = (df["beg_ue_date"] - df[employment_start_col]).dt.days
        df.loc[df["relevant_ue"] != 1, "tsince_ein_erw1"] = np.nan
        df["tsince_ein_erw1_cat"] = 99999
        df.loc[
            (df["tsince_ein_erw1"] > 0) & (df["tsince_ein_erw1"] <= 365),
            "tsince_ein_erw1_cat",
        ] = 1
        df.loc[
            (df["tsince_ein_erw1"] > 365) & (df["tsince_ein_erw1"] <= 1825),
            "tsince_ein_erw1_cat",
        ] = 2
        df.loc[
            (df["tsince_ein_erw1"] > 1825) & (df["tsince_ein_erw1"] <= 3650),
            "tsince_ein_erw1_cat",
        ] = 3
        df.loc[df["tsince_ein_erw1"] > 3650, "tsince_ein_erw1_cat"] = 3

    # time since last contact with labour market
    lm_contact_df = df[
        (df["episode_start_date"] < df["beg_relevant_ue_date"]) & (df["behspell"] == 1)
    ].copy()

    if len(lm_contact_df) > 0:
        lm_contact_df["lm_contact_date"] = lm_contact_df.groupby("person_id")[
            "episode_end_date"
        ].transform("max")
        if "part_time" in lm_contact_df.columns:
            lm_contact_df["ft_lm_contact_date"] = (
                lm_contact_df[lm_contact_df["part_time"] != 1]
                .groupby("person_id")["episode_end_date"]
                .transform("max")
            )

        lm_cols = ["lm_contact_date"]
        if "ft_lm_contact_date" in lm_contact_df.columns:
            lm_cols.append("ft_lm_contact_date")
        lm_contact_summary = (
            lm_contact_df.groupby("person_id").first()[lm_cols].reset_index()
        )
        df = df.merge(lm_contact_summary, on="person_id", how="left")

        df["tsince_lm_contact"] = (df["beg_ue_date"] - df["lm_contact_date"]).dt.days
        df.loc[df["relevant_ue"] != 1, "tsince_lm_contact"] = np.nan
        if "ft_lm_contact_date" in df.columns:
            df["tsince_ft_lm_contact"] = (
                df["beg_relevant_ue_date"] - df["ft_lm_contact_date"]
            ).dt.days
            df.loc[df["relevant_ue"] != 1, "tsince_ft_lm_contact"] = np.nan

        for var in ["tsince_lm_contact", "tsince_ft_lm_contact"]:
            if var in df.columns:
                df[f"{var}_cat"] = 5
                df.loc[df[var] <= 92, f"{var}_cat"] = 1
                df.loc[(df[var] > 92) & (df[var] <= 184), f"{var}_cat"] = 2
                df.loc[(df[var] > 184) & (df[var] <= 365), f"{var}_cat"] = 3
                df.loc[df[var] > 365, f"{var}_cat"] = 4

    # characteristics of last job
    lastjob_df = df[
        (df["episode_start_date"] < df["beg_relevant_ue_date"]) & (df["behspell"] == 1)
    ].copy()

    if len(lastjob_df) > 0 and job_duration_col is not None:
        lastjob_df["last_job_end"] = np.where(
            lastjob_df["episode_end_date"]
            == lastjob_df.groupby("person_id")["episode_end_date"].transform("max"),
            1,
            0,
        )
        lastjob_df = lastjob_df[lastjob_df["last_job_end"] == 1].copy()
        lastjob_df = lastjob_df.sort_values(
            ["person_id", job_duration_col, "daily_wage"],
            ascending=[True, False, False],
        )
        lastjob_df["nrLEmp"] = lastjob_df.groupby("person_id").cumcount() + 1
        lastjob_df = lastjob_df[lastjob_df["nrLEmp"] == 1].copy()

        lastjob_cols = [
            job_duration_col,
            "pg5",
            "part_time",
            "wage_defl",
            "occ_blo",
            "occupation_skill_level",
            "temporary_employment",
            "fixed_term_employment",
            "education_level_imputed",
            "district_region",
            "industry_destatis",
        ]
        available_cols = [col for col in lastjob_cols if col in lastjob_df.columns]
        lastjob_summary = lastjob_df[["person_id"] + available_cols].copy()
        lastjob_summary = lastjob_summary.drop_duplicates(
            subset="person_id", keep="first"
        )
        rename_dict = {
            job_duration_col: "lastjob_tot_dur",
            "pg5": "lastjob_type",
            "part_time": "lastjob_pt",
            "wage_defl": "lastjob_wage_defl",
            "occ_blo": "lastjob_occblo",
            "occupation_skill_level": "lastjob_niveau",
            "temporary_employment": "lastjob_leih",
            "fixed_term_employment": "lastjob_befrist",
            "education_level_imputed": "lastjob_educ",
            "district_region": "lastjob_ao_kreis",
            "industry_destatis": "lastjob_industry_destatis",
        }
        lastjob_summary = lastjob_summary.rename(columns=rename_dict)
        df = df.merge(lastjob_summary, on="person_id", how="left")
        df["lastjob_none"] = df["lastjob_tot_dur"].isna().astype(int)

        for col in lastjob_summary.columns:
            if col != "person_id":
                if col in ["lastjob_tot_dur", "lastjob_wage_defl"]:
                    df.loc[df["lastjob_none"] == 1, col] = 0
                else:
                    df.loc[df["lastjob_none"] == 1, col] = 99999
                    df[col] = df[col].fillna(99999)

    
    return df


def index_unemployment_entries(df: pd.DataFrame,
                               year_range: list[int]=list(range(2010, 2018)),
                               ) -> pd.DataFrame:
    """
    Indexes all entries into unemployment for each individual. This function
    is based on Stata code provided by Hannah Mautner.

    The function creates a variable 'nrEntry' that numbers each unemployment
    entry chronologically for each person, allowing the analysis to track
    multiple unemployment episodes per individual. The indexing is done only
    for unemployment entries that begin during 2010-2017.

    Args:
        df (pd.DataFrame): Dataset containing unemployment entry information.
            Expected columns include: person_id, spell_count, beg_ue, and year.

    Returns:
        pd.DataFrame: Dataset with added 'nrEntry' column indicating the entry
            number for each unemployment episode.
    """

    # work on copy of dataframe
    df = df.copy()

    ### JUDGMENT CALL: why the choice of 2010-2017 specifically?
    # filter to only unemployment entries (beg_ue == 1) in years 2010-2017
    entry_df = df[(df["beg_ue"] == 1) & (df["year"].isin(year_range))].copy()

    # sort by person and spell to ensure chronological order
    entry_df = entry_df.sort_values(["person_id", "spell_count"])

    # generate index for unemployment entries per person
    entry_df["nrEntry"] = entry_df.groupby("person_id").cumcount() + 1

    # keep only necessary columns for merge
    entry_df = entry_df[["person_id", "spell_count", "nrEntry"]]

    # merge back to full dataset
    df = df.merge(entry_df, on=["person_id", "spell_count"], how="left")

    return df
