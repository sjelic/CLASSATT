from unittest.mock import MagicMock

import pytest

from prisutnosti import session
from prisutnosti.checker import AttendanceChecker


def test_login_uses_esalter_fields_without_human_check(monkeypatch):
    page = MagicMock()
    locators = {}

    def locator(selector):
        return locators.setdefault(selector, MagicMock())

    page.locator.side_effect = locator
    expected = MagicMock()
    monkeypatch.setattr(session, "expect", expected)
    session.PlaywrightSessionManager(page).login("teacher", "secret")
    locators["#kime"].fill.assert_called_once_with("teacher")
    locators["#lozinka"].fill.assert_called_once_with("secret")
    assert not any("human" in selector for selector in locators)
    page.wait_for_function.assert_not_called()
    locators["#btnSubMitc"].click.assert_called_once_with()
    assert page.goto.call_args_list[-1].args == (session.LOGIN_URL,)
    assert page.goto.call_count == 1
    expected.return_value.to_be_visible.assert_called_once()


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
    assert checker._filename("QRCODE", {"Kod predmeta": "../ABC", "Datum prisustva": "01/04/2026", "Vreme pocetka": "10:00"}, ".png") == "QRCODE_.._ABC_01_04_2026_10_00_UNKNOWN.png"


@pytest.mark.parametrize("failure", [AssertionError("Missing field"), session.PlaywrightError("Missing field")])
def test_missing_login_success_element_raises_error_without_redirect(monkeypatch, failure):
    page = MagicMock()
    expected = MagicMock()
    expected.return_value.to_be_visible.side_effect = failure
    monkeypatch.setattr(session, "expect", expected)
    with pytest.raises(session.LoginError, match="expected element.*was not found"):
        session.PlaywrightSessionManager(page).login("user", "wrong")
    assert page.goto.call_count == 1
    assert page.goto.call_args.args == (session.LOGIN_URL,)
    page.wait_for_function.assert_not_called()


def test_successful_login_verifies_authentication_without_command_navigation(monkeypatch):
    page = MagicMock()
    page.locator.return_value.count.return_value = 0
    expected = MagicMock()
    monkeypatch.setattr(session, "expect", expected)
    session.PlaywrightSessionManager(page).login(
        "user", "secret", success_selector=session.AUTHENTICATED_SELECTOR,
    )
    assert page.goto.call_args.args == (session.LOGIN_URL,)
    assert page.goto.call_count == 1
    assert page.locator.call_args_list[-1].args == (session.AUTHENTICATED_SELECTOR,)
    expected.return_value.to_be_visible.assert_called_once_with(timeout=30_000)
