from __future__ import annotations

from getpass import getpass
import re

from playwright.sync_api import Page, expect

LOGIN_URL = "https://esalter.grf.bg.ac.rs/nastavnik/index.php"


class PlaywrightSessionManager:
    """Authenticate the page used by all subsequent attendance operations."""

    def __init__(self, page: Page, login_url: str = LOGIN_URL) -> None:
        self.page = page
        self.login_url = login_url

    def login(self, username: str, password: str) -> None:
        self.page.goto(self.login_url, wait_until="domcontentloaded")
        self.page.locator('#kime, input[name="email"]').fill(username)
        self.page.locator('#lozinka, input[name="password"]').fill(password)
        human = self.page.locator('input[name="human"]')
        if human.count():
            prompt = human.get_attribute("placeholder") or ""
            match = re.fullmatch(r"\s*(\d+)\s*(?:PLUS|\+)\s*(\d+)\s*=\s*\?\s*", prompt, re.I)
            if not match:
                raise ValueError("Unrecognized login arithmetic question.")
            human.fill(str(int(match[1]) + int(match[2])))
        self.page.locator(
            '#btnSubMitc, button[name="submit"][type="submit"], '
            'input[name="submit"][type="submit"]'
        ).click()
        # Verify access to the protected attendance page, rather than treating
        # submission or a redirect as proof of successful authentication.
        from .checker import CHECK_URL
        self.page.goto(CHECK_URL, wait_until="domcontentloaded")
        expect(self.page.locator("#dataTables-studenti")).to_be_visible(timeout=30_000)


def prompt_credentials() -> tuple[str, str]:
    username = input("Username/email: ").strip()
    password = getpass("Password: ")
    if not username or not password:
        raise ValueError("Username/email and password must not be empty.")
    return username, password
