from datetime import datetime
from unittest.mock import MagicMock
import logging

import pytest

from prisutnosti.single_creator import AttendanceTermCreator, CREATE_URL
from prisutnosti import commands


PARAMETERS = dict(date="2026-04-01", time="10:00:00", link_duration=30,
                  course_code="ABC", activation="selected", room="A1")


def test_existing_attendance_skips_form_and_reports_message(caplog):
    caplog.set_level(logging.INFO)
    page, checker = MagicMock(), MagicMock()
    checker.check.return_value = [{"existing": True}]
    assert AttendanceTermCreator(page, checker).create_term(**PARAMETERS) is False
    page.goto.assert_not_called()
    page.locator.assert_not_called()
    checker.check.assert_called_once_with(date="2026-04-01", time="10:00:00", course_code="ABC", room="A1")
    assert "Skipping existing attendance" in caplog.text


@pytest.mark.parametrize("date", ["2026-04-01", datetime(2026, 4, 1)])
def test_new_attendance_checks_before_creation_then_verifies(date):
    page, checker = MagicMock(), MagicMock()
    checker.check.side_effect = [[], [{"created": True}]]
    creator = AttendanceTermCreator(page, checker)
    creator._select_value = MagicMock()
    def navigating(*args, **kwargs):
        assert checker.check.call_count == 1
    page.goto.side_effect = navigating
    assert creator.create_term(**{**PARAMETERS, "date": date}) is True
    page.goto.assert_called_once_with(CREATE_URL, wait_until="domcontentloaded")
    assert checker.check.call_count == 2
    assert checker.check.call_args_list[0] == checker.check.call_args_list[1]
    page.locator.return_value.click.assert_called()


def test_lookup_failure_never_creates_attendance():
    page, checker = MagicMock(), MagicMock()
    checker.check.side_effect = RuntimeError("Search failed")
    with pytest.raises(RuntimeError, match="Search failed"):
        AttendanceTermCreator(page, checker).create_term(**PARAMETERS)
    page.goto.assert_not_called()


def test_single_command_reports_skip(monkeypatch):
    creator = MagicMock()
    creator.create_term.return_value = False
    monkeypatch.setattr(commands, "AttendanceTermCreator", lambda page: creator)
    result = commands.create_term(MagicMock(), **PARAMETERS)
    assert result.output == "Attendance already exists; skipped."
    assert result.exit_code == 0
