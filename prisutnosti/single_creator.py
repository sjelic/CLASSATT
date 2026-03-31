from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.select import Select

from .checker import AttendanceChecker

CREATE_URL = "https://esalter.grf.bg.ac.rs/nastavnik/form_kreiraj_prisustvo.php"


class AttendanceTermCreator:
    def __init__(self, driver: WebDriver, checker: AttendanceChecker | None = None) -> None:
        self.driver = driver
        self.checker = checker or AttendanceChecker(driver)

    def create_term(
        self,
        date: str,
        time: str,
        link_duration: int,
        course_code: str,
        activation: str,
        room: str,
    ) -> None:
        self.driver.get(CREATE_URL)
        self.driver.find_element(By.CSS_SELECTOR, "#datumprisustvo").send_keys(date)

        self._select_value("#vremeprisustvo", time)
        self._select_value("#salaprisustvo", room)
        self._select_value("#trajanjelinka", str(link_duration))
        self._select_value("#aktivacija", activation)
        self._select_value("#predmet", course_code)

        self.driver.find_element(By.CSS_SELECTOR, "#btnSubMitc").click()

        created = self.checker.check(date=date, time=time, course_code=course_code, room=room)
        if not created:
            raise RuntimeError("Attendance term was not created.")

    def _select_value(self, selector: str, value: str) -> None:
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        select = Select(element)
        values = [option.get_attribute("value") for option in select.options]
        if value not in values:
            raise ValueError(f"Value '{value}' not available for selector '{selector}'")
        select.select_by_value(value)
