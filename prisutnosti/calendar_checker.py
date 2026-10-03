"""Check each attendance in an Excel calendar using one authenticated page."""
from dataclasses import dataclass
import logging

from .checker import AttendanceChecker
from .loader import dataframe_to_terms, load_terms_dataframe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarCheckResult:
    checked: int
    failed: int


class CalendarAttendanceChecker:
    def __init__(self, checker: AttendanceChecker) -> None:
        self.checker = checker

    def check_from_excel(self, *, excel_path: str, excel_sheet: str, course_code: str,
                         download_list: bool = False, list_directory: str | None = None,
                         download_qrcode: bool = False, qrcode_directory: str | None = None) -> CalendarCheckResult:
        if download_list and not list_directory:
            raise ValueError("list_directory is required when downloading attendance lists.")
        if download_qrcode and not qrcode_directory:
            raise ValueError("qrcode_directory is required when downloading QR codes.")
        terms = dataframe_to_terms(load_terms_dataframe(excel_path, excel_sheet))
        checked = failed = 0
        for index, term in enumerate(terms, start=1):
            date = term.registration_start.strftime("%Y-%m-%d")
            time = term.registration_start.strftime("%H:%M:%S")
            logger.info("Checking calendar row %d/%d: course=%s date=%s time=%s room=%s",
                        index, len(terms), course_code, date, time, term.room)
            try:
                self.checker.check(date=date, time=time, course_code=course_code, room=term.room,
                                   download_list=download_list, list_directory=list_directory,
                                   download_qrcode=download_qrcode, qrcode_directory=qrcode_directory)
                checked += 1
            except Exception as exc:
                failed += 1
                logger.error("Calendar row %d failed: %s", index, exc)
        logger.info("Calendar check complete: total=%d checked=%d failed=%d", len(terms), checked, failed)
        return CalendarCheckResult(checked, failed)
