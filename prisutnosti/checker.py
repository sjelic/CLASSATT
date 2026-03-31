from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

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


class AttendanceChecker:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

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
        self.driver.get(CHECK_URL)

        terms = [value for value in [date, course_code, room, time] if value]
        query = " ".join(terms)
        self.driver.find_element(By.CSS_SELECTOR, "#dataTables-studenti_filter > label > input").send_keys(query)

        results: list[dict[str, Any]] = []
        pagination = self.driver.find_element(By.CSS_SELECTOR, "#dataTables-studenti_paginate > ul")
        pages = pagination.find_elements(By.CSS_SELECTOR, "li a")

        for page_link in pages:
            page_link.click()
            headers = [
                self._to_latin(header.text.strip())
                for header in self.driver.find_elements(By.CSS_SELECTOR, "#dataTables-studenti > thead > tr > th")
            ]
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#dataTables-studenti > tbody > tr")

            for row_index, row in enumerate(rows, start=1):
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                row_dict = {headers[i]: cells[i].text.strip() for i in range(min(len(headers), len(cells)))}
                results.append(row_dict)

                if download_list and list_directory:
                    self._download_list(row_index, row_dict, list_directory)

                if download_qrcode and qrcode_directory:
                    self._download_qrcode_if_available(row, row_dict, qrcode_directory)

        return results

    def _download_list(self, row_index: int, row_dict: dict[str, Any], directory: str) -> None:
        submit = self.driver.find_element(
            By.CSS_SELECTOR,
            f"#raporti_prisustvo_id > input[type=submit]:nth-child({row_index})",
        )
        submit.click()
        self.driver.find_element(
            By.CSS_SELECTOR,
            "#dataTables-studenti_wrapper > div.dt-buttons.btn-group > button.btn.btn-secondary.buttons-excel.buttons-html5",
        ).click()

        filename = (
            f"PRISUTNOST_{row_dict.get('Sifra','UNKNOWN')}_{row_dict.get('Datum','UNKNOWN')}"
            f"_{row_dict.get('Vreme','UNKNOWN')}_{row_dict.get('Sala','UNKNOWN')}.xlsx"
        )
        Path(directory).mkdir(parents=True, exist_ok=True)
        Path(directory, filename).touch(exist_ok=True)

    def _download_qrcode_if_available(self, row: Any, row_dict: dict[str, Any], directory: str) -> None:
        cells = row.find_elements(By.CSS_SELECTOR, "td")
        if len(cells) < 9:
            return

        status_cell = cells[8]
        status_cell.click()
        img = self.driver.find_element(By.CSS_SELECTOR, "#qrModal > div > div > div.modal-body > img")
        src = img.get_attribute("src")
        if not src or not src.startswith("data:image/png;base64,"):
            return

        payload = src.split(",", maxsplit=1)[1]
        data = base64.b64decode(payload)

        filename = (
            f"QRCODE_{row_dict.get('Sifra','UNKNOWN')}_{row_dict.get('Datum','UNKNOWN')}"
            f"_{row_dict.get('Vreme','UNKNOWN')}_{row_dict.get('Sala','UNKNOWN')}.png"
        )
        Path(directory).mkdir(parents=True, exist_ok=True)
        Path(directory, filename).write_bytes(data)

    def _to_latin(self, text: str) -> str:
        return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)
