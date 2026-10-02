from __future__ import annotations

import logging

from getpass import getpass

from playwright.sync_api import Error as PlaywrightError, Page, expect

logger = logging.getLogger(__name__)


class LoginError(RuntimeError):
    """Authentication failed; browser actions must not proceed."""

LOGIN_URL = "https://esalter.grf.bg.ac.rs/nastavnik"
AUTHENTICATED_SELECTOR = "#navbarDropdownPortfolio"


class PlaywrightSessionManager:
    """Authenticate the page used by all subsequent attendance operations."""

    def __init__(self, page: Page, login_url: str = LOGIN_URL) -> None:
        self.page = page
        self.login_url = login_url

    def login(
        self, username: str, password: str,
        success_selector: str = "#dataTables-studenti",
    ) -> None:
        logger.info("Starting login")
        try:
            self._login(username, password, success_selector)
        except (PlaywrightError, AssertionError, ValueError) as exc:
            raise LoginError("Login failed: credentials were rejected or authentication could not be verified.") from exc

    def _login(self, username: str, password: str, success_selector: str) -> None:
        logger.info("Opening login page: %s", self.login_url)
        self.page.goto(self.login_url, wait_until="domcontentloaded")
        logger.info("Opening sign-in form")
        self.page.locator('#navbarResponsive ul[class="navbar-nav ml-auto"] li[class="nav-item"] a').click()
        self.page.locator('#kime').fill(username)
        self.page.locator('#lozinka').fill(password)
        logger.info("Submitting login form")
        self.page.locator("#btnSubMitc").click()

        logger.info("Verifying authenticated session")
        try:
            expect(self.page.locator(success_selector)).to_be_visible(timeout=30_000)
        except (PlaywrightError, AssertionError) as exc:
            raise LoginError(
                f"Login failed: expected element '{success_selector}' was not found "
                "after submitting login."
            ) from exc
        logger.info("Login verified")


def prompt_credentials() -> tuple[str, str]:
    username = input("Username/email: ").strip()
    password = getpass("Password: ")
    if not username or not password:
        raise ValueError("Username/email and password must not be empty.")
    return username, password
