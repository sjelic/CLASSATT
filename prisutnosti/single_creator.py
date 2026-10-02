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
        
        date.year, date.month, date.day  # validate date format
        self.page.locator("#datumprisustvo").click()
        
        self.page.locator("body > div.datepicker.datepicker-dropdown.dropdown-menu.datepicker-orient-left.datepicker-orient-top > div.datepicker-days > table > thead > tr > th.datepicker-switch").click()
        
        self.page.locator("body > div.datepicker.datepicker-dropdown.dropdown-menu.datepicker-orient-left.datepicker-orient-top > div.datepicker-months > table > thead > tr > th.datepicker-switch").click()
        
        self.page.locator("body > div.datepicker.datepicker-dropdown.dropdown-menu.datepicker-orient-left.datepicker-orient-top > div.datepicker-years > table > tbody > tr > td > span").get_by_text(f"{date.year}").click()
        
        self.page.locator("body > div.datepicker.datepicker-dropdown.dropdown-menu.datepicker-orient-left.datepicker-orient-top > div.datepicker-months > table > tbody > tr > td > span").get_by_text(f"{date.strftime('%b')}").click()
        
        self.page.locator("body > div.datepicker.datepicker-dropdown.dropdown-menu.datepicker-orient-left.datepicker-orient-top > div.datepicker-days > table > tbody > tr > td.day:not(.new)").get_by_text(f"{date.day}", exact=True).click()
        
        self._select_value("#vremeprisustvo", time)
        self._select_value("#salaprisustvo", room)
        self._select_value("#trajanjeprisustvo", str(link_duration))
        self._select_value("#aktivacijaprisustvo", activation)
        self._select_value("#sifraPredmet", course_code) 
        self.page.locator("#btnSubMitc").click()

        created = self.checker.check(date=date.strftime("%Y-%m-%d"), time=time, course_code=course_code, room=room)
        if not created:
            raise RuntimeError("Attendance term was not created.")

    def _select_value(self, selector: str, value: str) -> None:
        element = self.page.locator(selector)
        values = element.locator("option").evaluate_all("options => options.map(option => option.value)")
        if value not in values:
            raise ValueError(f"Value '{value}' not available for selector '{selector}'")
        element.select_option(value=value)
