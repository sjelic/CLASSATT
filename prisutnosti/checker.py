from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Locator, expect

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
    ) -> list[dict[str, Any]]:
        
        
        self.page.goto(CHECK_URL, wait_until="domcontentloaded")
        
        
        if download_list and not list_directory:
            raise ValueError("list_directory is required when downloading attendance lists.")
        if download_qrcode and not qrcode_directory:
            raise ValueError("qrcode_directory is required when downloading QR codes.")
        query = " ".join(value for value in [date, course_code, room, time] if value)
        print(f"Searching for attendance terms matching: {query}")
        self._open_results(query)
        headers = [self._to_latin(text.strip()) for text in
                   self.page.locator("#dataTables-studenti > thead > tr > th").all_text_contents()]
        results: list[dict[str, Any]] = []
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
                print(row_dict)
                results.append(row_dict)
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
            self.page.evaluate("index => jQuery('#dataTables-studenti').DataTable().page(index).draw('page')", page_index)
        return results

    @staticmethod
    def _filename(prefix: str, row_dict: dict[str, Any], extension: str) -> str:
        # Prevent values from the page (e.g. dates containing '/') becoming paths.
        parts = [str(row_dict.get(key, "UNKNOWN")) for key in ("Kod predmeta", "Datum prisustva", "Vreme pocetka", "Sala")]
        return prefix + "_" + "_".join(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", part) for part in parts) + extension

    def _download_list(self, row: Locator, row_dict: dict[str, Any], directory: str) -> None:
        row.locator('#raporti_prisustvo_id input[value="СПИСАК СТУДЕНАТА"]').click()
        export = self.page.locator(
            "#dataTables-studenti_wrapper > div.dt-buttons.btn-group > "
            "button.btn.btn-secondary.buttons-excel.buttons-html5"
        )
        with self.page.expect_download() as pending:
            export.click()
        Path(directory).mkdir(parents=True, exist_ok=True)
        pending.value.save_as(Path(directory, self._filename("PRISUTNOST", row_dict, ".xlsx")))

    def _download_qrcode_if_available(self, row: Locator, row_dict: dict[str, Any], directory: str) -> None:
        cells = row.locator("td")
        if cells.count() < 9:
            return
        status = cells.nth(8)
        # Only open a QR modal for rows whose status has a modal trigger.
        trigger = status.locator('[data-target="#qrModal"], [data-bs-target="#qrModal"]')
        if trigger.count():
            trigger.first.click()
        elif status.get_attribute("onclick"):
            status.click()
        else:
            return
        modal = self.page.locator("#qrModal")
        expect(modal).to_be_visible()
        try:
            img = modal.locator("div.modal-body > img")
            expect(img).to_be_visible()
            src = img.get_attribute("src") or ""
            if src.startswith("data:image/png;base64,"):
                data = base64.b64decode(src.split(",", 1)[1], validate=True)
                Path(directory).mkdir(parents=True, exist_ok=True)
                Path(directory, self._filename("QRCODE", row_dict, ".png")).write_bytes(data)
        finally:
            modal.locator('[data-dismiss="modal"], [data-bs-dismiss="modal"], button.close').first.click()
            expect(modal).to_be_hidden()

    def _to_latin(self, text: str) -> str:
        return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)
