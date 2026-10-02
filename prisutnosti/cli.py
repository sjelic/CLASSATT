from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from .bulk_creator import BulkAttendanceCreator
from .checker import AttendanceChecker, CHECK_URL
from .loader import load_terms_dataframe
from .session import LoginError, PlaywrightSessionManager, prompt_credentials
from .single_creator import AttendanceTermCreator, CREATE_URL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prisutnosti", description="Attendance management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    load_parser = sub.add_parser("load", help="Load and validate terms from Excel")
    load_parser.add_argument("--excel-path", required=True)
    load_parser.add_argument("--excel-sheet", required=True)

    sub.add_parser("login", help="Verify login using prompted credentials")

    create_term_parser = sub.add_parser("create-term", help="Create a single attendance term")
    create_term_parser.add_argument("--date", required=True)
    create_term_parser.add_argument("--time", required=True)
    create_term_parser.add_argument("--link-duration", required=True, type=int)
    create_term_parser.add_argument("--course-code", required=True)
    create_term_parser.add_argument("--activation", required=True, choices=["selected", "ne"])
    create_term_parser.add_argument("--room", required=True)

    create_parser = sub.add_parser("create", help="Create attendance terms from Excel")
    create_parser.add_argument("--excel-path", required=True)
    create_parser.add_argument("--excel-sheet", required=True)
    create_parser.add_argument("--course-code", required=True)

    check_parser = sub.add_parser("check", help="Check existing attendance terms")
    check_parser.add_argument("--date")
    check_parser.add_argument("--time")
    check_parser.add_argument("--course-code")
    check_parser.add_argument("--room")
    check_parser.add_argument("--download-list", choices=["yes", "no"], default="no")
    check_parser.add_argument("--list-directory")
    check_parser.add_argument("--download-qrcode", choices=["yes", "no"], default="no")
    check_parser.add_argument("--qrcode-directory")

    return parser


@contextmanager
def _browser_page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(30_000)
            yield page
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "load":
        df = load_terms_dataframe(args.excel_path, args.excel_sheet)
        print(f"Loaded {len(df)} rows successfully.")
        return 0

    try:
        username, password = prompt_credentials()
    except ValueError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1
    with _browser_page() as page:
        creating = args.command in {"create-term", "create"}
        try:
            PlaywrightSessionManager(page).login(
                username, password,
                landing_url=CREATE_URL if creating else CHECK_URL,
                success_selector="#navbarDropdownPortfolio",
            )
        except LoginError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.command == "login":
            print("Login verified.")
            return 0

        if args.command == "create-term":
            creator = AttendanceTermCreator(page)
            creator.create_term(
                date=args.date,
                time=args.time,
                link_duration=args.link_duration,
                course_code=args.course_code,
                activation=args.activation,
                room=args.room,
            )
            print("Attendance term created.")
            return 0

        if args.command == "create":
            result = BulkAttendanceCreator(AttendanceTermCreator(page)).create_from_excel(
                excel_path=args.excel_path,
                excel_sheet=args.excel_sheet,
                course_code=args.course_code,
            )
            print(json.dumps(asdict(result), ensure_ascii=False))
            return 0 if result.failed == 0 else 1

        if args.command == "check":
            checker = AttendanceChecker(page)
            result = checker.check(
                date=args.date,
                time=args.time,
                course_code=args.course_code,
                room=args.room,
                download_list=args.download_list == "yes",
                list_directory=args.list_directory,
                download_qrcode=args.download_qrcode == "yes",
                qrcode_directory=args.qrcode_directory,
            )
            print(json.dumps(result, ensure_ascii=False))
            return 0

        parser.error("Unknown command")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
