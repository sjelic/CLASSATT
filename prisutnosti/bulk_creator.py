from __future__ import annotations

from dataclasses import dataclass

from .loader import dataframe_to_terms, load_terms_dataframe
from .single_creator import AttendanceTermCreator


@dataclass(slots=True)
class BulkCreateResult:
    created: int
    failed: int
    errors: list[str]


class BulkAttendanceCreator:
    def __init__(self, term_creator: AttendanceTermCreator) -> None:
        self.term_creator = term_creator

    def create_from_excel(self, excel_path: str, excel_sheet: str, course_code: str) -> BulkCreateResult:
        df = load_terms_dataframe(excel_path, excel_sheet)
        terms = dataframe_to_terms(df)

        created = 0
        failed = 0
        errors: list[str] = []

        for index, term in enumerate(terms, start=1):
            try:
                self.term_creator.create_term(
                    date=term.starts_at.strftime("%Y-%m-%d"),
                    time=term.registration_start.strftime("%H:%M:%S"),
                    link_duration=term.link_duration_minutes,
                    course_code=course_code,
                    activation=term.activation,
                    room=term.room,
                )
                created += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"Row {index}: {exc}")

        return BulkCreateResult(created=created, failed=failed, errors=errors)
