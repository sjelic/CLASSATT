from __future__ import annotations

import logging

import base64
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Locator, expect

logger = logging.getLogger(__name__)

CHECK_URL = "https://esalter.grf.bg.ac.rs/nastavnik/form_pregled_prisustvo.php"

CYRILLIC_TO_LATIN = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Ђ": "Dj",
    "Е": "E",
    "Ж": "Z",
    "З": "Z",
    "И": "I",
    "Ј": "J",
    "К": "K",
    "Л": "L",
    "Љ": "Lj",
    "М": "M",
    "Н": "N",
    "Њ": "Nj",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "Ћ": "C",
    "У": "U",
    "Ф": "F",
    "Х": "H",
    "Ц": "C",
    "Ч": "C",
    "Џ": "Dz",
    "Ш": "S",
}

CYRILLIC_TO_LATIN.update({key.lower(): value.lower() for key, value in list(CYRILLIC_TO_LATIN.items())})


class AttendanceChecker:
    def __init__(self, page: Page) -> None:
        self.page = page

    def _open_results(self, query: str, page_index: int = 0) -> None:
        logger.info("Opening attendance overview: %s", CHECK_URL)
        self.page.goto(CHECK_URL, wait_until="domcontentloaded")
        expect(self.page.locator("#dataTables-studenti_filter input")).to_be_visible()
        self.page.locator("#dataTables-studenti_filter input").fill(query)
        self.page.locator("#dataTables-studenti_filter input").press("Enter")
        # DataTables' synchronous draw avoids reading stale rows after filtering.
        self.page.wait_for_function("""() => window.jQuery &&
            jQuery.fn.dataTable && jQuery.fn.dataTable.isDataTable('#dataTables-studenti')""")
        self.page.evaluate("""([query, index]) => {
            const table = jQuery('#dataTables-studenti').DataTable();
            table.search(query).draw();
            table.page(index).draw('page');
        }""", [query, page_index])

    def check(
        self,
        date: str | None = None,
        time: str | None = None,
        course_code: str | None = None,
        room: str | None = None,
        download_list: bool = False,
        list_directory: str | None = None,
        download_qrcode: bool = False,
        qrcode_directory: str | None = None,
    ) -> None:
        
        
        logger.info("Opening attendance overview: %s", CHECK_URL)
        self.page.goto(CHECK_URL, wait_until="domcontentloaded")
        
        
        if download_list and not list_directory:
            raise ValueError("list_directory is required when downloading attendance lists.")
        if download_qrcode and not qrcode_directory:
            raise ValueError("qrcode_directory is required when downloading QR codes.")
        query = " ".join(value for value in [date, course_code, room, time] if value)
        logger.info("Finding attendance terms matching: %s", query)
        self._open_results(query)
        headers = [self._to_latin(text.strip()) for text in
                   self.page.locator("#dataTables-studenti > thead > tr > th").all_text_contents()]
        found_count = 0
        page_index = 0
        while True:
            rows = self.page.locator("#dataTables-studenti > tbody > tr")
            row_count = rows.count()
            for row_index in range(row_count):
                row = rows.nth(row_index)
                if row.locator("td.dataTables_empty").count():
                    continue
                cells = [text.strip() for text in row.locator("td").all_text_contents()]
                row_dict = dict(zip(headers, cells))
                logger.info("Found attendance row %d on page %d", row_index + 1, page_index + 1)
                logger.info("Attendance details: %s", row_dict)
                found_count += 1
                if download_qrcode:
                    self._download_qrcode_if_available(row, row_dict, qrcode_directory)
                if download_list:
                    self._download_list(row, row_dict, list_directory)
                    # Report navigation replaces the table. Rebuild the filtered
                    # page before resolving the next row's locator.
                    self._open_results(query, page_index)
            info = self.page.evaluate("() => jQuery('#dataTables-studenti').DataTable().page.info()")
            if page_index + 1 >= info["pages"]:
                break
            page_index += 1
            logger.info("Reading attendance page %d", page_index + 1)
            self.page.evaluate("index => jQuery('#dataTables-studenti').DataTable().page(index).draw('page')", page_index)
        logger.info("Found %d matching attendance terms", found_count)
        return

    def exists(self, *, date: str, time: str, course_code: str, room: str) -> bool:
        """Internal existence query without returning attendance records."""
        self._open_results(" ".join([date, course_code, room, time]))
        info = self.page.evaluate("() => jQuery('#dataTables-studenti').DataTable().page.info()")
        return info["recordsDisplay"] > 0

    @staticmethod
    def _filename(prefix: str, row_dict: dict[str, Any], extension: str) -> str:
        # Prevent values from the page (e.g. dates containing '/') becoming paths.
        parts = [str(row_dict.get(key, "UNKNOWN")) for key in ("Kod predmeta", "Datum prisustva", "Vreme pocetka", "Sala")]
        return prefix + "_" + "_".join(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", part) for part in parts) + extension

    def _download_list(self, row: Locator, row_dict: dict[str, Any], directory: str) -> None:
        logger.info("Opening attendance list report")
        row.locator('#raporti_prisustvo_id input[value="СПИСАК СТУДЕНАТА"]').click()
        export = self.page.locator(
            "#dataTables-studenti_wrapper > div.dt-buttons.btn-group > "
            "button.btn.btn-secondary.buttons-excel.buttons-html5"
        )
        logger.info("Downloading attendance list")
        with self.page.expect_download() as pending:
            export.click()
        Path(directory).mkdir(parents=True, exist_ok=True)
        filepath = Path(directory, self._filename("PRISUTNOST", row_dict, ".xlsx"))
        pending.value.save_as(filepath)
        logger.info("Attendance list saved: %s", filepath)

    @staticmethod
    def _available_path(directory: str, filename: str) -> Path:
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / filename
        index = 2
        while filepath.exists():
            filepath = folder / f"{Path(filename).stem}_{index}{Path(filename).suffix}"
            index += 1
        return filepath

    def _download_qrcode_if_available(self, row: Locator, row_dict: dict[str, Any], directory: str) -> None:
        logger.info("Checking QR code availability")
        # Scope triggers to the current record, rather than selecting every
        # matching QR element in the table and causing a strict-mode violation.
        triggers = row.locator('[data-target="#qrModal"], [data-bs-target="#qrModal"]')
        cells = row.locator("td")
        fallback = cells.nth(8) if cells.count() >= 9 else None
        trigger_count = triggers.count()
        if not trigger_count and (fallback is None or not fallback.get_attribute("onclick")):
            logger.info("No QR code available for this attendance")
            return
        for trigger_index in range(trigger_count or 1):
            if trigger_count:
                triggers.nth(trigger_index).click()
            else:
                fallback.click()
            # Hidden modals with the same ID must not match the image lookup.
            modal = self.page.locator("#qrModal:visible").first
            expect(modal).to_be_visible()
            try:
                images = modal.locator("div.modal-body > img")
                expect(images.first).to_be_visible()
                for image_index in range(images.count()):
                    src = images.nth(image_index).get_attribute("src") or ""
                    if not src.startswith("data:image/png;base64,"):
                        logger.warning("QR image has no supported PNG data URL; skipping")
                        continue
                    data = base64.b64decode(src.split(",", 1)[1], validate=True)
                    filepath = self._available_path(directory, self._filename("QRCODE", row_dict, ".png"))
                    filepath.write_bytes(data)
                    logger.info("QR code saved: %s", filepath)
            finally:
                modal.locator('[data-dismiss="modal"], [data-bs-dismiss="modal"], button.close').first.click()
                expect(modal).to_be_hidden()

    def _to_latin(self, text: str) -> str:
        return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)
