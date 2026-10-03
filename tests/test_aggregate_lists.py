from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from openpyxl import Workbook

from prisutnosti.calendar_checker import CalendarAttendanceChecker
from prisutnosti.list_aggregator import AttendanceListAggregator
from prisutnosti import cli


def calendar(tmp_path):
    rows = []
    for day, kind in [(8, "PREDAVANJE"), (9, "VEŽBE")]:
        start = pd.Timestamp(2026, 10, day, 13)
        rows.append({"ОД": start, "ДО": start + pd.Timedelta(hours=1), "САЛА": "A1",
                     "ПОЧЕТАК ПРИЈАВЕ": start + pd.Timedelta(minutes=15),
                     "ТРАЈАЊЕ ЛИНКА": 30, "АКТИВАЦИЈА": "selected", "ТИП НАСТАВЕ": kind})
    path = tmp_path / "calendar.xlsx"
    pd.DataFrame(rows).to_excel(path, sheet_name="Calendar", index=False)
    return path


def test_only_current_downloads_are_aggregated_with_correct_row_metadata(tmp_path):
    workbook = calendar(tmp_path)
    directory = tmp_path / "lists"
    directory.mkdir()
    pd.DataFrame({"Student": ["STALE"]}).to_excel(directory / "old.xlsx", index=False)
    checker = MagicMock()
    def check(**kwargs):
        assert kwargs["download_list"] is True
        number = 2 if kwargs["date"] == "2026-10-08" else 1
        for index in range(number):
            path = directory / f"{kwargs['date']}-{index}.xlsx"
            pd.DataFrame({"Student": [f"Student-{kwargs['date']}-{index}"], "Index": ["001"]}).to_excel(path, index=False)
            kwargs["on_list_downloaded"](path)
    checker.check.side_effect = check
    operation = CalendarAttendanceChecker(checker)
    result = operation.check_from_excel(excel_path=str(workbook), excel_sheet="Calendar", course_code="ABC",
                                        aggregate_lists=True, list_directory=str(directory))
    assert (result.checked, result.failed) == (2, 0)
    assert result.aggregate_path.name == "PRISUTNOST_ZBIRNO_ABC.xlsx"
    records = pd.read_excel(result.aggregate_path, dtype={"Index": str})
    assert len(records) == 3
    assert list(records.columns) == ["Student", "Index", "TIP NASTAVE", "OD", "DO", "POČETAK PRIJAVE"]
    assert records["TIP NASTAVE"].tolist() == ["PREDAVANJE", "PREDAVANJE", "VEŽBE"]
    assert records["Index"].tolist() == ["001"] * 3
    assert records.iloc[2]["OD"] == pd.Timestamp(2026, 10, 9, 13)
    assert records.iloc[2]["POČETAK PRIJAVE"] == pd.Timestamp(2026, 10, 9, 13, 15)
    assert not records["Student"].str.contains("STALE").any()
    # Re-running replaces the aggregate rather than duplicating student rows.
    operation.check_from_excel(excel_path=str(workbook), excel_sheet="Calendar", course_code="ABC",
                              aggregate_lists=True, list_directory=str(directory))
    assert len(pd.read_excel(result.aggregate_path)) == 3
    assert (directory / "old.xlsx").exists()


def test_merged_export_title_is_not_a_student_record(tmp_path):
    path = tmp_path / "individual.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Attendance report"])
    sheet.merge_cells("A1:B1")
    sheet.append(["Student", "Index"])
    sheet.append(["Ana", "001"])
    workbook.save(path)
    output = tmp_path / "all.xlsx"
    aggregator = AttendanceListAggregator(output)
    metadata = {"TIP NASTAVE": "VEŽBE", "OD": datetime(2026, 10, 8, 13),
                "DO": datetime(2026, 10, 8, 14), "POČETAK PRIJAVE": datetime(2026, 10, 8, 13, 15)}
    aggregator.add(path, metadata)
    aggregator.write()
    result = pd.read_excel(output)
    assert len(result) == 1 and result.iloc[0]["Student"] == "Ana"


def test_aggregation_requires_teaching_type_but_disabled_mode_does_not(tmp_path):
    workbook = calendar(tmp_path)
    df = pd.read_excel(workbook).drop(columns="ТИП НАСТАВЕ")
    df.to_excel(workbook, sheet_name="Calendar", index=False)
    checker = MagicMock()
    operation = CalendarAttendanceChecker(checker)
    args = dict(excel_path=str(workbook), excel_sheet="Calendar", course_code="ABC")
    assert operation.check_from_excel(**args).checked == 2
    with pytest.raises(ValueError, match="ТИП НАСТАВЕ"):
        operation.check_from_excel(**args, aggregate_lists=True, list_directory=str(tmp_path))


def test_aggregate_option_defaults_and_alias():
    args = ["check-calendar", "--excel-path", "calendar.xlsx", "--excel-sheet", "Calendar", "--course-code", "ABC"]
    assert cli.build_parser().parse_args(args).aggregate_lists == "no"
    assert cli.build_parser().parse_args(args + ["--aggregated-lists", "yes"]).aggregate_lists == "yes"


def test_download_callback_receives_saved_file(tmp_path):
    from prisutnosti.checker import AttendanceChecker
    page, row = MagicMock(), MagicMock()
    pending = page.expect_download.return_value.__enter__.return_value
    pending.value.save_as.side_effect = lambda path: pd.DataFrame({"Student": ["Ana"]}).to_excel(path, index=False)
    received = []
    def callback(path):
        assert pd.read_excel(path).iloc[0]["Student"] == "Ana"
        received.append(path)
    AttendanceChecker(page)._download_list(row, {"Kod predmeta": "ABC"}, str(tmp_path), callback)
    assert len(received) == 1 and received[0].exists()


def test_aggregate_cannot_overwrite_individual_list(tmp_path):
    path = tmp_path / "individual.xlsx"
    pd.DataFrame({"Student": ["Ana"]}).to_excel(path, index=False)
    before = path.read_bytes()
    aggregator = AttendanceListAggregator(path)
    with pytest.raises(ValueError, match="cannot replace"):
        aggregator.add(path, {})
    with pytest.raises(ValueError, match="conflicts"):
        aggregator.write()
    assert path.read_bytes() == before
