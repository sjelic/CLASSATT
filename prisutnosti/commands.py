"""Command operations independent of argument parsing and console output."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from playwright.sync_api import Page

from .bulk_creator import BulkAttendanceCreator
from .checker import AttendanceChecker
from .loader import load_terms_dataframe
from .single_creator import AttendanceTermCreator


@dataclass(frozen=True)
class CommandResult:
    output: str
    exit_code: int = 0


def load(*, excel_path: str, excel_sheet: str) -> CommandResult:
    df = load_terms_dataframe(excel_path, excel_sheet)
    return CommandResult(f"Loaded {len(df)} rows successfully.")


def login() -> CommandResult:
    # Authentication is completed by the shared CLI lifecycle before dispatch.
    return CommandResult("Login verified.")


def create_term(page: Page, *, date: str, time: str, link_duration: int,
                course_code: str, activation: str, room: str) -> CommandResult:
    was_created = AttendanceTermCreator(page).create_term(
        date=date, time=time, link_duration=link_duration,
        course_code=course_code, activation=activation, room=room,
    )
    if was_created is False:
        return CommandResult("Attendance already exists; skipped.")
    return CommandResult("Attendance term created.")


def create(page: Page, *, excel_path: str, excel_sheet: str, course_code: str) -> CommandResult:
    result = BulkAttendanceCreator(AttendanceTermCreator(page)).create_from_excel(
        excel_path=excel_path, excel_sheet=excel_sheet, course_code=course_code,
    )
    return CommandResult(json.dumps(asdict(result), ensure_ascii=False), 0 if result.failed == 0 else 1)


def check(page: Page, *, date: str | None = None, time: str | None = None,
          course_code: str | None = None, room: str | None = None,
          download_list: bool = False, list_directory: str | None = None,
          download_qrcode: bool = False, qrcode_directory: str | None = None) -> None:
    AttendanceChecker(page).check(
        date=date, time=time, course_code=course_code, room=room,
        download_list=download_list, list_directory=list_directory,
        download_qrcode=download_qrcode, qrcode_directory=qrcode_directory,
    )
    return
