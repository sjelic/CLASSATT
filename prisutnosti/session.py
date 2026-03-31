from __future__ import annotations

from getpass import getpass

from selenium.webdriver.remote.webdriver import WebDriver

LOGIN_URL = "https://esalter.grf.bg.ac.rs/nastavnik/index.php"


class SeleniumSessionManager:
    """Logs in and keeps an authorized Selenium session alive through browser cookies."""

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def login(self, username: str, password: str) -> None:
        self.driver.get(LOGIN_URL)
        self.driver.find_element("css selector", "#kime").send_keys(username)
        self.driver.find_element("css selector", "#lozinka").send_keys(password)
        self.driver.find_element("css selector", "#btnSubMitc").click()


def prompt_credentials() -> tuple[str, str]:
    username = input("Username: ")
    password = getpass("Password: ")
    return username, password
