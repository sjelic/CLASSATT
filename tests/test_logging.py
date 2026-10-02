import logging
from unittest.mock import MagicMock

import pytest

from prisutnosti import cli, session


def test_login_steps_are_logged_without_credentials(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="prisutnosti")
    page = MagicMock()
    monkeypatch.setattr(session, "expect", MagicMock())
    session.PlaywrightSessionManager(page).login("private-user", "private-password")
    for step in ["Starting login", "Opening sign-in form", "Submitting login form",
                 "Verifying authenticated session", "Login verified"]:
        assert step in caplog.text
    assert "private-user" not in caplog.text
    assert "private-password" not in caplog.text


@pytest.mark.parametrize("code,level", [(0, logging.INFO), (1, logging.ERROR)])
def test_result_logging_preserves_exit_status(caplog, code, level):
    caplog.set_level(logging.INFO, logger="prisutnosti")
    assert cli._log_result(cli.commands.CommandResult("summary", code)) == code
    assert caplog.records[-1].levelno == level
    assert caplog.records[-1].getMessage() == "summary"


def test_operation_failure_is_logged_and_reraised(monkeypatch, caplog):
    error = ValueError("invalid operation")
    def fail(*args):
        raise error
    monkeypatch.setattr(cli, "_dispatch", fail)
    with pytest.raises(ValueError) as caught:
        cli._run_command(cli.build_parser().parse_args(["check"]), MagicMock())
    assert caught.value is error
    assert "Command check failed (ValueError)" in caplog.text
