# imports
import pandas as pd


def translate_to_english(df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates the column names of the SIAB data from German to English.

    The English variable names are inspired by the descriptions from the data
    documentation at https://doku.iab.de/fdz/reporte/2023/DR_01-23_EN.pdf.

    Args:
        df (pd.DataFrame): DataFrame with German column names.
    Returns:
        pd.DataFrame: DataFrame with English column names.
    """

    # german -> english feature name mapping
    translation_dict = {
        "persnr_siab_r": "person_id",
        "bnn": "establishment_id",
        "spell": "spell_count",
        "quelle_gr": "spell_source",
        "begorig": "observation_start_date",
        "endorig": "observation_end_date",
        "begepi": "episode_start_date",
        "endepi": "episode_end_date",
        "frau": "female",
        "gebjahr": "birth_year",
        "deutsch": "german_citizen",
        "ausbildung_gr": "education_level",
        "ausbildung_imp": "education_level_imputed",
        "schule": "school_completed",
        "tentgelt_gr": "daily_wage",
        "beruf_gr": "occupation_group_1988",
        "beruf2010_gr": "occupation_group_2010",
        "niveau": "occupation_skill_level",
        "teilzeit": "part_time",
        "stib": "working_hours",
        "erwstat_gr": "employment_status_group",
        "gleitz": "transition_zone",
        "leih": "temporary_employment",
        "befrist": "fixed_term_employment",
        "grund_gr": "termination_reason_group",
        "tage_jung": "days_employed_before_17",
        "tage_alt": "days_employed_after_62",
        "alo_dau": "unemployment_duration_days",
        "ao_region": "district_region",
        "pendler": "commuter",
        "w08_gen_gr": "wage_group",
    }

    df = df.rename(columns=translation_dict)

    return df
