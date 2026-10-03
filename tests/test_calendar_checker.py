from contextlib import contextmanager
from unittest.mock import MagicMock

import pandas as pd
import pytest

from prisutnosti.calendar_checker import CalendarAttendanceChecker
from prisutnosti import cli, commands


def make_workbook(tmp_path):
    rows = []
    for day, room in [(8, "322"), (9, "A1"), (10, "A2")]:
        start = pd.Timestamp(2026, 10, day, 13, 0)
        rows.append({"ОД": start, "ДО": start + pd.Timedelta(hours=1), "САЛА": room,
                     "ПОЧЕТАК ПРИЈАВЕ": start + pd.Timedelta(minutes=15),
                     "ТРАЈАЊЕ ЛИНКА": 30, "АКТИВАЦИЈА": "selected"})
    path = tmp_path / "calendar.xlsx"
    pd.DataFrame(rows).to_excel(path, sheet_name="Calendar", index=False)
    return dict(excel_path=str(path), excel_sheet="Calendar", course_code="ABC")


def test_all_rows_use_registration_date_time_room_and_download_options(tmp_path):
    options = make_workbook(tmp_path)
    checker = MagicMock()
    result = CalendarAttendanceChecker(checker).check_from_excel(
        **options, download_list=True, list_directory="lists", download_qrcode=True, qrcode_directory="qr")
    assert (result.checked, result.failed) == (3, 0)
    assert checker.check.call_count == 3
    for call, day, room in zip(checker.check.call_args_list, [8, 9, 10], ["322", "A1", "A2"]):
        assert call.kwargs == dict(date=f"2026-10-{day:02d}", time="13:15:00", course_code="ABC", room=room,
                                   download_list=True, list_directory="lists", download_qrcode=True, qrcode_directory="qr")


def test_row_error_is_logged_and_next_rows_are_checked(tmp_path, caplog):
    checker = MagicMock()
    checker.check.side_effect = [None, RuntimeError("Download failed"), None]
    result = CalendarAttendanceChecker(checker).check_from_excel(**make_workbook(tmp_path))
    assert (result.checked, result.failed) == (2, 1)
    assert checker.check.call_count == 3
    assert "Calendar row 2 failed" in caplog.text


def test_invalid_download_configuration_fails_before_check(tmp_path):
    checker = MagicMock()
    with pytest.raises(ValueError, match="qrcode_directory"):
        CalendarAttendanceChecker(checker).check_from_excel(**make_workbook(tmp_path), download_qrcode=True)
    checker.check.assert_not_called()


def test_cli_authenticates_once_before_processing_all_calendar_rows(tmp_path, monkeypatch, caplog):
    options = make_workbook(tmp_path)
    events = []
    page = MagicMock()
    @contextmanager
    def browser():
        yield page
        events.append("closed")
    session = MagicMock()
    session.login.side_effect = lambda *args, **kwargs: events.append("login")
    checker = MagicMock()
    def check(**kwargs):
        assert events[0] == "login"
        events.append("check")
    checker.check.side_effect = check
    monkeypatch.setattr(cli, "browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", lambda received: session)
    monkeypatch.setattr(commands, "AttendanceChecker", lambda received: checker)
    args = ["check-calendar"]
    for key, value in options.items():
        args.extend(["--" + key.replace("_", "-"), value])
    assert cli.main(args) == 0
    assert events == ["login", "check", "check", "check", "closed"]
    session.login.assert_called_once()
    assert "checked=3; failed=0" in caplog.text


def test_command_reports_nonzero_exit_for_row_failures(tmp_path, monkeypatch):
    checker = MagicMock()
    checker.check.side_effect = [None, RuntimeError("failed"), None]
    monkeypatch.setattr(commands, "AttendanceChecker", lambda page: checker)
    assert commands.check_calendar(MagicMock(), **make_workbook(tmp_path)).exit_code == 1
