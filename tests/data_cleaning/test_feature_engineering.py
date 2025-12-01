import pytest
import pandas as pd
import numpy as np
from data_cleaning.feature_engineering import (
    identify_unemployment_episodes,
    generate_biographical_variables,
    index_unemployment_entries
)


def test_identify_unemployment_episodes_basic():
    df = pd.DataFrame({
        "person_id": [1, 1, 1],
        "spell_count": [1, 2, 3],
        "episode_start_date": pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"]),
        "episode_end_date": pd.to_datetime(["2020-01-31", "2020-02-28", "2020-03-31"]),
        "spell_source": [5, 5, 5],
        "employment_status_group": [21, 21, 21],
        "birth_year": [1980, 1980, 1980]
    })
    result = identify_unemployment_episodes(df)
    assert "seeking1" in result.columns
    assert "beg_ue" in result.columns


def test_generate_biographical_variables_basic():
    df = pd.DataFrame({
        "person_id": [1, 1],
        "spell_count": [1, 2],
        "episode_start_date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
        "episode_end_date": pd.to_datetime(["2020-01-31", "2020-02-28"]),
        "observation_start_date": pd.to_datetime(["2020-01-01", "2020-02-01"]),
        "spell_source": [1, 1],
        "employment_status_group": [1, 1],
        "daily_wage": [100, 120],
        "establishment_id": [1000, 1000]
    })
    result = generate_biographical_variables(df)
    assert "start_employment1" in result.columns
    assert "cum_days_emp1" in result.columns


def test_index_unemployment_entries_basic():
    df = pd.DataFrame({
        "person_id": [1, 1, 1],
        "spell_count": [1, 2, 3],
        "beg_ue": [1, 0, 1],
        "year": [2010, 2010, 2011]
    })
    result = index_unemployment_entries(df)
    assert "nrEntry" in result.columns


def test_index_unemployment_entries_filters_years():
    df = pd.DataFrame({
        "person_id": [1, 1],
        "spell_count": [1, 2],
        "beg_ue": [1, 1],
        "year": [2009, 2010]
    })
    result = index_unemployment_entries(df)
    assert result["nrEntry"].isna().sum() == 1
