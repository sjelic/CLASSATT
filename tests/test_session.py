from unittest.mock import MagicMock

import pytest

from prisutnosti import session
from prisutnosti.checker import AttendanceChecker, CHECK_URL


def test_login_uses_esalter_fields_without_human_check(monkeypatch):
    page = MagicMock()
    locators = {}

    def locator(selector):
        return locators.setdefault(selector, MagicMock())

    page.locator.side_effect = locator
    locator('#lozina, input[name="lozinka"]').count.return_value = 0
    expected = MagicMock()
    monkeypatch.setattr(session, "expect", expected)
    session.PlaywrightSessionManager(page).login("teacher", "secret")
    locators['#kime, input[name="kime"]'].fill.assert_called_once_with("teacher")
    locators['#lozina, input[name="lozinka"]'].fill.assert_called_once_with("secret")
    assert not any("human" in selector for selector in locators)
    page.wait_for_function.assert_not_called()
    locators["#btnSubMitc"].click.assert_called_once_with()
    assert page.goto.call_args_list[-1].args == (CHECK_URL,)
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
    assert checker._filename("QRCODE", {"Sifra": "../ABC", "Datum": "01/04/2026", "Vreme": "10:00"}, ".png") == "QRCODE_.._ABC_01_04_2026_10_00_UNKNOWN.png"


@pytest.mark.parametrize("failure", [AssertionError("Missing field"), session.PlaywrightError("Missing field")])
def test_missing_landing_field_raises_error_after_redirect(monkeypatch, failure):
    page = MagicMock()
    expected = MagicMock()
    expected.return_value.to_be_visible.side_effect = failure
    monkeypatch.setattr(session, "expect", expected)
    with pytest.raises(session.LoginError, match="expected element.*was not found"):
        session.PlaywrightSessionManager(page).login("user", "wrong")
    assert page.goto.call_count == 2
    assert page.goto.call_args.args == (CHECK_URL,)
    page.wait_for_function.assert_not_called()


def test_successful_login_opens_and_verifies_creation_page(monkeypatch):
    from prisutnosti.single_creator import CREATE_URL
    page = MagicMock()
    page.locator.return_value.count.return_value = 0
    expected = MagicMock()
    monkeypatch.setattr(session, "expect", expected)
    session.PlaywrightSessionManager(page).login(
        "user", "secret", landing_url=CREATE_URL, success_selector="#datumprisustvo",
    )
    assert page.goto.call_args.args == (CREATE_URL,)
    assert page.locator.call_args_list[-1].args == ("#datumprisustvo",)
    expected.return_value.to_be_visible.assert_called_once_with(timeout=30_000)
