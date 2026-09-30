from __future__ import annotations

from playwright.sync_api import Page

from .checker import AttendanceChecker

CREATE_URL = "https://esalter.grf.bg.ac.rs/nastavnik/form_kreiraj_prisustvo.php"


class AttendanceTermCreator:
    def __init__(self, page: Page, checker: AttendanceChecker | None = None) -> None:
        self.page = page
        self.checker = checker or AttendanceChecker(page)

    def create_term(
        self,
        date: str,
        time: str,
        link_duration: int,
        course_code: str,
        activation: str,
        room: str,
    ) -> None:
        self.page.goto(CREATE_URL, wait_until="domcontentloaded")
        self.page.locator("#datumprisustvo").fill(date)

        self._select_value("#vremeprisustvo", time)
        self._select_value("#salaprisustvo", room)
        self._select_value("#trajanjelinka", str(link_duration))
        self._select_value("#aktivacija", activation)
        self._select_value("#predmet", course_code)

        self.page.locator("#btnSubMitc").click()

        created = self.checker.check(date=date, time=time, course_code=course_code, room=room)
        if not created:
            raise RuntimeError("Attendance term was not created.")

    def _select_value(self, selector: str, value: str) -> None:
        element = self.page.locator(selector)
        values = element.locator("option").evaluate_all("options => options.map(option => option.value)")
        if value not in values:
            raise ValueError(f"Value '{value}' not available for selector '{selector}'")
        element.select_option(value=value)
