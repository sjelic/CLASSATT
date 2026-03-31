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
