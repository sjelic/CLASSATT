from unittest.mock import MagicMock

import pytest

from prisutnosti import session
from prisutnosti.checker import AttendanceChecker, CHECK_URL


@pytest.mark.parametrize("question,answer", [("12 PLUS 7 = ?", "19"), ("3 + 4 = ?", "7")])
def test_login_answers_arithmetic_and_verifies_protected_page(monkeypatch, question, answer):
    page = MagicMock()
    locators = {}

    def locator(selector):
        return locators.setdefault(selector, MagicMock())

    page.locator.side_effect = locator
    human = locator('input[name="human"]')
    human.count.return_value = 1
    human.get_attribute.return_value = question
    expected = MagicMock()
    monkeypatch.setattr(session, "expect", expected)
    session.PlaywrightSessionManager(page).login("person@example.com", "secret")
    human.fill.assert_called_once_with(answer)
    assert page.goto.call_args_list[-1].args == (CHECK_URL,)
    expected.return_value.to_be_visible.assert_called_once()


def test_login_rejects_unrecognized_question_without_submitting(monkeypatch):
    page = MagicMock()
    page.locator.return_value.get_attribute.return_value = "Unexpected question"
    with pytest.raises(ValueError, match="Unrecognized"):
        session.PlaywrightSessionManager(page).login("user", "secret")
    page.locator.return_value.click.assert_not_called()


def test_prompt_hides_password_and_requires_nonempty_values(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "  person@example.com ")
    monkeypatch.setattr(session, "getpass", lambda _: "secret")
    assert session.prompt_credentials() == ("person@example.com", "secret")
    monkeypatch.setattr(session, "getpass", lambda _: "")
    with pytest.raises(ValueError, match="must not be empty"):
        session.prompt_credentials()


def test_artifact_names_transliterate_headers_and_cannot_escape_directory():
    checker = AttendanceChecker(MagicMock())
    assert checker._to_latin("Шифра") == "Sifra"
    assert checker._filename("QRCODE", {"Sifra": "../ABC", "Datum": "01/04/2026", "Vreme": "10:00"}, ".png") == "QRCODE_.._ABC_01_04_2026_10_00_UNKNOWN.png"
