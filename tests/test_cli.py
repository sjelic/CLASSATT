from __future__ import annotations

import pandas as pd
import pytest

from prisutnosti import cli


def test_cli_load_command(tmp_path, capsys) -> None:
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
    out = capsys.readouterr().out

    assert rc == 0
    assert "Loaded 1 rows successfully." in out


def test_create_authenticates_before_bulk_and_serializes_summary(monkeypatch, capsys):
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
            assert kwargs["landing_url"] == cli.CREATE_URL
            assert (username, password) == ("user", "secret")
            events.append("login")

    class Bulk:
        def __init__(self, creator):
            pass

        def create_from_excel(self, **kwargs):
            assert events == ["login"]
            events.append("create")
            return BulkCreateResult(created=1, failed=0, errors=[])

    monkeypatch.setattr(cli, "_browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", Session)
    monkeypatch.setattr(cli, "BulkAttendanceCreator", Bulk)
    assert cli.main(["create", "--excel-path", "terms.xlsx", "--excel-sheet", "Data", "--course-code", "ABC"]) == 0
    assert events == ["login", "create", "closed"]
    assert '"created": 1' in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [
    ["login"],
    ["create", "--excel-path", "terms.xlsx", "--excel-sheet", "Data", "--course-code", "ABC"],
    ["create-term", "--date", "2026-04-01", "--time", "10:00:00", "--link-duration", "30",
     "--course-code", "ABC", "--activation", "selected", "--room", "A1"],
    ["check"],
])
def test_login_failure_reports_error_closes_browser_and_blocks_actions(monkeypatch, capsys, arguments):
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

    monkeypatch.setattr(cli, "_browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", Session)
    def forbidden(*args, **kwargs):
        pytest.fail("Attendance action must not run after login failure")

    monkeypatch.setattr(cli, "AttendanceTermCreator", forbidden)
    monkeypatch.setattr(cli, "BulkAttendanceCreator", forbidden)
    monkeypatch.setattr(cli, "AttendanceChecker", forbidden)
    assert cli.main(arguments) == 1
    assert "Login failed" in capsys.readouterr().err
    assert events == ["closed"]
