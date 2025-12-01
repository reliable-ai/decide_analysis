import pandas as pd
from read_data.translate_names import translate_to_english


def test_translate_to_english_renames_columns():
    df = pd.DataFrame({"persnr_siab_r": [1, 2], "bnn": [100, 200], "frau": [0, 1]})
    result = translate_to_english(df)
    assert "person_id" in result.columns
    assert "establishment_id" in result.columns
    assert "female" in result.columns


def test_translate_to_english_preserves_data():
    df = pd.DataFrame({"persnr_siab_r": [1, 2, 3]})
    result = translate_to_english(df)
    assert len(result) == 3
    assert result["person_id"].tolist() == [1, 2, 3]
