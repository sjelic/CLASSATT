from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from prisutnosti.loader import load_terms_dataframe, validate_terms_dataframe


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ОД": ["2026-04-01 10:00:00"],
            "ДО": ["2026-04-01 12:00:00"],
            "САЛА": ["A1"],
            "ПОЧЕТАК ПРИЈАВЕ": ["2026-04-01 10:15:00"],
            "ТРАЈАЊЕ ЛИНКА": [30],
            "АКТИВАЦИЈА": ["selected"],
        }
    )


def test_validate_terms_dataframe_passes_for_valid_data() -> None:
    validate_terms_dataframe(_valid_df())


def test_validate_terms_dataframe_raises_when_required_column_missing() -> None:
    df = _valid_df().drop(columns=["АКТИВАЦИЈА"])
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_terms_dataframe(df)


def test_validate_terms_dataframe_raises_when_registration_window_outside_term() -> None:
    df = _valid_df()
    df.loc[0, "ПОЧЕТАК ПРИЈАВЕ"] = "2026-04-01 11:45:00"
    df.loc[0, "ТРАЈАЊЕ ЛИНКА"] = 30

    with pytest.raises(ValueError, match="must be within"):
        validate_terms_dataframe(df)


def test_load_terms_dataframe_from_excel(tmp_path: Path) -> None:
    excel = tmp_path / "terms.xlsx"
    _valid_df().to_excel(excel, sheet_name="Sheet1", index=False)

    loaded = load_terms_dataframe(str(excel), "Sheet1")
    assert len(loaded) == 1
    assert list(loaded.columns)[:3] == ["ОД", "ДО", "САЛА"]
