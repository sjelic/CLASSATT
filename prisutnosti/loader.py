from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

REQUIRED_COLUMNS = ["ОД", "ДО", "САЛА", "ПОЧЕТАК ПРИЈАВЕ", "ТРАЈАЊЕ ЛИНКА", "АКТИВАЦИЈА"]


@dataclass(slots=True)
class LoadedTerm:
    starts_at: datetime
    ends_at: datetime
    room: str
    registration_start: datetime
    link_duration_minutes: int
    activation: str


def load_terms_dataframe(excel_path: str, excel_sheet: str) -> pd.DataFrame:
    """Load the attendance table from an Excel workbook sheet into a DataFrame."""
    df = pd.read_excel(excel_path, sheet_name=excel_sheet)
    validate_terms_dataframe(df)
    return df


def validate_terms_dataframe(df: pd.DataFrame) -> None:
    """Validate required structure and temporal constraints for loaded terms."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    for index, row in df.iterrows():
        starts_at = pd.to_datetime(row["ОД"])
        ends_at = pd.to_datetime(row["ДО"])
        registration_start = pd.to_datetime(row["ПОЧЕТАК ПРИЈАВЕ"])

        try:
            duration_minutes = int(row["ТРАЈАЊЕ ЛИНКА"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid 'ТРАЈАЊЕ ЛИНКА' at row {index + 2}: {row['ТРАЈАЊЕ ЛИНКА']}") from exc

        if starts_at >= ends_at:
            raise ValueError(f"'ОД' must be less than 'ДО' at row {index + 2}")

        if starts_at.date() > ends_at.date():
            raise ValueError(f"Date part of 'ОД' must not be greater than 'ДО' at row {index + 2}")

        registration_end = registration_start + timedelta(minutes=duration_minutes)
        if registration_start < starts_at or registration_end > ends_at:
            raise ValueError(
                "'ПОЧЕТАК ПРИЈАВЕ' + 'ТРАЈАЊЕ ЛИНКА' must be within ['ОД', 'ДО'] "
                f"at row {index + 2}"
            )


def dataframe_to_terms(df: pd.DataFrame) -> list[LoadedTerm]:
    """Convert a validated DataFrame into typed term objects."""
    validate_terms_dataframe(df)
    terms: list[LoadedTerm] = []
    for _, row in df.iterrows():
        terms.append(
            LoadedTerm(
                starts_at=pd.to_datetime(row["ОД"]).to_pydatetime(),
                ends_at=pd.to_datetime(row["ДО"]).to_pydatetime(),
                room=str(row["САЛА"]),
                registration_start=pd.to_datetime(row["ПОЧЕТАК ПРИЈАВЕ"]).to_pydatetime(),
                link_duration_minutes=int(row["ТРАЈАЊЕ ЛИНКА"]),
                activation=str(row["АКТИВАЦИЈА"]),
            )
        )
    return terms
