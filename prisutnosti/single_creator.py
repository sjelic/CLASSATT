from __future__ import annotations

import logging
from datetime import date as Date, datetime

from playwright.sync_api import Page

from .checker import AttendanceChecker

logger = logging.getLogger(__name__)

CREATE_URL = "https://esalter.grf.bg.ac.rs/nastavnik/form_kreiraj_prisustvo.php"


class AttendanceTermCreator:
    def __init__(self, page: Page, checker: AttendanceChecker | None = None) -> None:
        self.page = page
        self.checker = checker or AttendanceChecker(page)

    def create_term(
        self,
        date: str | Date,
        time: str,
        link_duration: int,
        course_code: str,
        activation: str,
        room: str,
    ) -> bool:
        """Return False for an existing attendance, True after creating one."""
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()
        search = dict(date=date.strftime("%Y-%m-%d"), time=time, course_code=course_code, room=room)
        logger.info("Checking attendance before creation: date=%s time=%s course=%s room=%s",
                    search["date"], time, course_code, room)
        if self.checker.exists(**search):
            logger.info("Skipping existing attendance: course=%s date=%s time=%s room=%s",
                        course_code, search["date"], time, room)
            return False
        self.page.goto(CREATE_URL, wait_until="domcontentloaded")
        
        logger.info("Selecting attendance date: %s", search["date"])
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
        logger.info("Submitting attendance form: date=%s time=%s", search["date"], time)
        # Finish the form POST/redirect before the checker navigates away.
        with self.page.expect_navigation(wait_until="domcontentloaded"):
            self.page.locator("#btnSubMitc").click()
        logger.info("Attendance form submission completed; verifying created attendance: date=%s time=%s",
                    search["date"], time)

        created = self.checker.exists(**search)
        if not created:
            logger.error("Created attendance could not be found")
            raise RuntimeError("Attendance was submitted, but the checker could not find it in the overview.")
        return True

    def _select_value(self, selector: str, value: str) -> None:
        logger.info("Selecting %s = %s", selector, value)
        element = self.page.locator(selector)
        values = element.locator("option").evaluate_all("options => options.map(option => option.value)")
        if value not in values:
            raise ValueError(f"Value '{value}' not available for selector '{selector}'")
        element.select_option(value=value)
