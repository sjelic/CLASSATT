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
    checker.exists.return_value = True
    assert AttendanceTermCreator(page, checker).create_term(**PARAMETERS) is False
    page.goto.assert_not_called()
    page.locator.assert_not_called()
    checker.exists.assert_called_once_with(date="2026-04-01", time="10:00:00", course_code="ABC", room="A1")
    assert "Skipping existing attendance" in caplog.text


@pytest.mark.parametrize("date", ["2026-04-01", datetime(2026, 4, 1)])
def test_new_attendance_checks_before_creation_then_verifies(date):
    page, checker = MagicMock(), MagicMock()
    checker.exists.side_effect = [False, True]
    creator = AttendanceTermCreator(page, checker)
    creator._select_value = MagicMock()
    def navigating(*args, **kwargs):
        assert checker.exists.call_count == 1
    page.goto.side_effect = navigating
    assert creator.create_term(**{**PARAMETERS, "date": date}) is True
    page.goto.assert_called_once_with(CREATE_URL, wait_until="domcontentloaded")
    assert checker.exists.call_count == 2
    assert checker.exists.call_args_list[0] == checker.exists.call_args_list[1]
    page.locator.return_value.click.assert_called()


def test_lookup_failure_never_creates_attendance():
    page, checker = MagicMock(), MagicMock()
    checker.exists.side_effect = RuntimeError("Search failed")
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


def test_verification_waits_for_submission_navigation():
    page, checker = MagicMock(), MagicMock()
    events = []
    def exists(**kwargs):
        events.append('check')
        return events.count('check') == 2
    checker.exists.side_effect = exists
    navigation = page.expect_navigation.return_value
    navigation.__enter__.side_effect = lambda: events.append('waiting')
    navigation.__exit__.side_effect = lambda *args: events.append('submitted')
    page.locator.return_value.click.side_effect = lambda: events.append('click')
    creator = AttendanceTermCreator(page, checker)
    creator._select_value = MagicMock()
    assert creator.create_term(**PARAMETERS) is True
    assert events[-4:] == ['waiting', 'click', 'submitted', 'check']
    page.expect_navigation.assert_called_once_with(wait_until='domcontentloaded')


def test_submission_failure_does_not_run_post_creation_lookup():
    page, checker = MagicMock(), MagicMock()
    checker.exists.return_value = False
    page.expect_navigation.return_value.__exit__.side_effect = RuntimeError('Submission failed')
    creator = AttendanceTermCreator(page, checker)
    creator._select_value = MagicMock()
    with pytest.raises(RuntimeError, match='Submission failed'):
        creator.create_term(**PARAMETERS)
    assert checker.exists.call_count == 1


def test_missing_after_submission_reports_verification_failure():
    page, checker = MagicMock(), MagicMock()
    checker.exists.return_value = False
    creator = AttendanceTermCreator(page, checker)
    creator._select_value = MagicMock()
    with pytest.raises(RuntimeError, match='submitted, but the checker could not find'):
        creator.create_term(**PARAMETERS)
    assert checker.exists.call_count == 2
