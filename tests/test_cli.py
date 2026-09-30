from __future__ import annotations

import pandas as pd

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

        def login(self, username, password):
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


def test_browser_closes_when_operation_fails(monkeypatch):
    import pytest
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

        def login(self, *args):
            raise RuntimeError("Login failed")

    monkeypatch.setattr(cli, "_browser_page", browser)
    monkeypatch.setattr(cli, "prompt_credentials", lambda: ("user", "secret"))
    monkeypatch.setattr(cli, "PlaywrightSessionManager", Session)
    with pytest.raises(RuntimeError, match="Login failed"):
        cli.main(["login"])
    assert events == ["closed"]
