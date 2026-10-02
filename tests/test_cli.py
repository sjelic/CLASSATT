from __future__ import annotations

import pandas as pd
import pytest

from prisutnosti import cli


def test_cli_load_command(tmp_path, caplog) -> None:
    excel = tmp_path / "terms.xlsx"
    df = pd.DataFrame(
        {
            "ОД": ["2026-04-01 10:00:00"],
            "ДО": ["2026-04-01 11:00:00"],
            "САЛА": ["A1"],
            "ПОЧЕТАК ПРИЈАВЕ": ["2026-04-01 10:05:00"],
            "ТРАЈАЊЕ ЛИНКА": [30],
            "АКТИВАЦИЈА": ["selected"],
        }
    )
    df.to_excel(excel, sheet_name="Data", index=False)

    rc = cli.main(["load", "--excel-path", str(excel), "--excel-sheet", "Data"])
    out = caplog.text

    assert rc == 0
    assert "Loaded 1 rows successfully." in out


def test_create_authenticates_before_bulk_and_serializes_summary(monkeypatch, caplog):
    from contextlib import contextmanager
    from prisutnosti.bulk_creator import BulkCreateResult

    events = []
    page = object()

    @contextmanager
    def browser():
        yield page
        events.append("closed")

    class Session:
        def __init__(self, received):
            assert received is page

        def login(self, username, password, **kwargs):
            assert kwargs == {"success_selector": cli.AUTHENTICATED_SELECTOR}
            assert (username, password) == ("user", "secret")
            events.append("login")

    class Bulk:
        def __init__(self, creator):
            pass

        def create_from_excel(self, **kwargs):
            assert events == ["login"]
            events.append("create")
            return BulkCreateResult(created=1, failed=0, errors=[])

    monkeypatch.setattr(cli, "browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", Session)
    monkeypatch.setattr(cli.commands, "BulkAttendanceCreator", Bulk)
    assert cli.main(["create", "--excel-path", "terms.xlsx", "--excel-sheet", "Data", "--course-code", "ABC"]) == 0
    assert events == ["login", "create", "closed"]
    assert '"created": 1' in caplog.text


@pytest.mark.parametrize("arguments", [
    ["login"],
    ["create", "--excel-path", "terms.xlsx", "--excel-sheet", "Data", "--course-code", "ABC"],
    ["create-term", "--date", "2026-04-01", "--time", "10:00:00", "--link-duration", "30",
     "--course-code", "ABC", "--activation", "selected", "--room", "A1"],
    ["check"],
])
def test_login_failure_reports_error_closes_browser_and_blocks_actions(monkeypatch, caplog, arguments):
    from contextlib import contextmanager

    events = []

    @contextmanager
    def browser():
        try:
            yield object()
        finally:
            events.append("closed")

    class Session:
        def __init__(self, page):
            pass

        def login(self, *args, **kwargs):
            raise cli.LoginError("Login failed")

    monkeypatch.setattr(cli, "browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", Session)
    def forbidden(*args, **kwargs):
        pytest.fail("Attendance action must not run after login failure")

    monkeypatch.setattr(cli.commands, "AttendanceTermCreator", forbidden)
    monkeypatch.setattr(cli.commands, "BulkAttendanceCreator", forbidden)
    monkeypatch.setattr(cli.commands, "AttendanceChecker", forbidden)
    assert cli.main(arguments) == 1
    assert "Login failed" in caplog.text
    assert events == ["closed"]


@pytest.mark.parametrize("arguments,operation,parameters", [
    (["load", "--excel-path", "terms.xlsx", "--excel-sheet", "Data"], "load",
     {"excel_path": "terms.xlsx", "excel_sheet": "Data"}),
    (["login"], "login", {}),
    (["create", "--excel-path", "terms.xlsx", "--excel-sheet", "Data", "--course-code", "ABC"], "create",
     {"excel_path": "terms.xlsx", "excel_sheet": "Data", "course_code": "ABC"}),
    (["create-term", "--date", "2026-04-01", "--time", "10:00:00", "--link-duration", "30",
      "--course-code", "ABC", "--activation", "selected", "--room", "A1"], "create_term",
     {"date": "2026-04-01", "time": "10:00:00", "link_duration": 30,
      "course_code": "ABC", "activation": "selected", "room": "A1"}),
    (["check", "--download-list", "yes", "--list-directory", "reports"], "check",
     {"date": None, "time": None, "course_code": None, "room": None,
      "download_list": True, "list_directory": "reports", "download_qrcode": False, "qrcode_directory": None}),
])
def test_dispatch_preserves_operation_parameters(monkeypatch, arguments, operation, parameters):
    from unittest.mock import Mock
    page = object()
    result = cli.commands.CommandResult("result", 1)
    handler = Mock(return_value=result)
    monkeypatch.setattr(cli.commands, operation, handler)
    assert cli._dispatch(cli.build_parser().parse_args(arguments), page) is result
    if operation in {"load", "login"}:
        handler.assert_called_once_with(**parameters)
    else:
        handler.assert_called_once_with(page, **parameters)


def test_load_never_prompts_or_opens_browser(monkeypatch, caplog):
    def forbidden(*args, **kwargs):
        pytest.fail("Load must not prompt or start a browser")

    monkeypatch.setattr(cli, "prompt_credentials", forbidden)
    monkeypatch.setattr(cli, "browser_page", forbidden)
    monkeypatch.setattr(cli.commands, "load", lambda **kwargs: cli.commands.CommandResult("Loaded 1 rows successfully."))
    assert cli.main(["load", "--excel-path", "terms.xlsx", "--excel-sheet", "Data"]) == 0
    assert "Loaded 1 rows successfully." in caplog.text
