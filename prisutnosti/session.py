from __future__ import annotations

from getpass import getpass
import re

from playwright.sync_api import Error as PlaywrightError, Page, expect

from .checker import CHECK_URL


class LoginError(RuntimeError):
    """Authentication failed; browser actions must not proceed."""

LOGIN_URL = "https://esalter.grf.bg.ac.rs/nastavnik/index.php"


class PlaywrightSessionManager:
    """Authenticate the page used by all subsequent attendance operations."""

    def __init__(self, page: Page, login_url: str = LOGIN_URL) -> None:
        self.page = page
        self.login_url = login_url

    def login(
        self, username: str, password: str,
        landing_url: str = CHECK_URL, success_selector: str = "#dataTables-studenti",
    ) -> None:
        try:
            self._login(username, password, landing_url, success_selector)
        except (PlaywrightError, AssertionError, ValueError) as exc:
            raise LoginError("Login failed: credentials were rejected or authentication could not be verified.") from exc

    def _login(self, username: str, password: str, landing_url: str, success_selector: str) -> None:
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
        # Wait for the login result before navigating away. Failed credentials
        # commonly leave the form visible and display an alert on the same URL.
        result = self.page.wait_for_function("""() => {
            const visible = element => !!(element && element.getClientRects().length);
            const alerts = [...document.querySelectorAll(
                '.alert-danger, [role="alert"], .invalid-feedback, .text-danger'
            )];
            if (alerts.some(element => visible(element) && element.textContent.trim())) return 'error';
            const fields = [...document.querySelectorAll('#lozinka, input[name="password"]')];
            if (!fields.some(visible)) return 'success';
            return false;
        }""").json_value()
        if result != "success":
            raise LoginError("Login failed: the login page reported an error. Check your credentials.")
        self.page.goto(landing_url, wait_until="domcontentloaded")
        expect(self.page.locator(success_selector)).to_be_visible(timeout=30_000)
        if self.page.locator('#lozinka, input[name="password"]').count():
            raise LoginError("Login failed: the requested page redirected back to login.")


def prompt_credentials() -> tuple[str, str]:
    username = input("Username/email: ").strip()
    password = getpass("Password: ")
    if not username or not password:
        raise ValueError("Username/email and password must not be empty.")
    return username, password
