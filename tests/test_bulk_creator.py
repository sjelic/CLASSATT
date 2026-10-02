from __future__ import annotations

from pathlib import Path

import pandas as pd

from prisutnosti.bulk_creator import BulkAttendanceCreator


class FakeTermCreator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_term(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["room"] == "FAIL":
            raise RuntimeError("boom")


def test_create_from_excel_continues_after_single_row_failure(tmp_path: Path) -> None:
    excel = tmp_path / "terms.xlsx"
    df = pd.DataFrame(
        {
            "ОД": ["2026-04-01 10:00:00", "2026-04-01 11:00:00"],
            "ДО": ["2026-04-01 10:45:00", "2026-04-01 12:00:00"],
            "САЛА": ["OK", "FAIL"],
            "ПОЧЕТАК ПРИЈАВЕ": ["2026-04-01 10:00:00", "2026-04-01 11:00:00"],
            "ТРАЈАЊЕ ЛИНКА": [30, 30],
            "АКТИВАЦИЈА": ["selected", "selected"],
        }
    )
    df.to_excel(excel, sheet_name="Raspored", index=False)

    fake = FakeTermCreator()
    result = BulkAttendanceCreator(fake).create_from_excel(str(excel), "Raspored", "MAT101")

    assert result.created == 1
    assert result.failed == 1
    assert len(result.errors) == 1
    assert len(fake.calls) == 2


def test_bulk_continues_after_skips_and_counts_created_skipped_failed(monkeypatch):
    from types import SimpleNamespace
    from datetime import datetime
    from unittest.mock import MagicMock
    from prisutnosti import bulk_creator
    terms = [SimpleNamespace(registration_start=datetime(2026, 4, 1, 10),
                            link_duration_minutes=30, activation="selected", room=room)
             for room in ["EXISTS", "NEW", "FAIL", "EXISTS_AGAIN"]]
    monkeypatch.setattr(bulk_creator, "load_terms_dataframe", lambda *args: object())
    monkeypatch.setattr(bulk_creator, "dataframe_to_terms", lambda df: terms)
    creator = MagicMock()
    creator.create_term.side_effect = [False, True, RuntimeError("failed"), False]
    result = BulkAttendanceCreator(creator).create_from_excel("test.xlsx", "Data", "ABC")
    assert (result.created, result.skipped, result.failed) == (1, 2, 1)
    assert result.errors == ["Row 3: failed"]
    assert creator.create_term.call_count == 4
