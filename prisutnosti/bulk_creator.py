from __future__ import annotations

import logging

from dataclasses import dataclass

from .loader import dataframe_to_terms, load_terms_dataframe
from .single_creator import AttendanceTermCreator


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BulkCreateResult:
    created: int
    failed: int
    errors: list[str]
    skipped: int = 0


class BulkAttendanceCreator:
    def __init__(self, term_creator: AttendanceTermCreator) -> None:
        self.term_creator = term_creator

    def create_from_excel(self, excel_path: str, excel_sheet: str, course_code: str) -> BulkCreateResult:
        logger.info("Starting bulk attendance creation for course %s", course_code)
        df = load_terms_dataframe(excel_path, excel_sheet)
        terms = dataframe_to_terms(df)

        created = 0
        failed = 0
        skipped = 0
        errors: list[str] = []

        for index, term in enumerate(terms, start=1):
            logger.info("Creating attendance row %d of %d", index, len(terms))
            try:
                was_created = self.term_creator.create_term(
                    date=term.registration_start,
                    time=term.registration_start.strftime("%H:%M:%S"),
                    link_duration=term.link_duration_minutes,
                    course_code=course_code,
                    activation=term.activation,
                    room=term.room,
                )
                if was_created is False:
                    skipped += 1
                    logger.info("Attendance row %d skipped: already exists", index)
                else:
                    created += 1
                    logger.info("Attendance row %d created", index)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                logger.error("Attendance row %d failed: %s", index, exc)
                errors.append(f"Row {index}: {exc}")


        return BulkCreateResult(created=created, failed=failed, errors=errors, skipped=skipped)
