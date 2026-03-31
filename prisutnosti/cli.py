from __future__ import annotations

import argparse
import json
from typing import Any

from selenium import webdriver

from .bulk_creator import BulkAttendanceCreator
from .checker import AttendanceChecker
from .loader import load_terms_dataframe
from .session import SeleniumSessionManager, prompt_credentials
from .single_creator import AttendanceTermCreator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prisutnosti", description="Attendance management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    load_parser = sub.add_parser("load", help="Load and validate terms from Excel")
    load_parser.add_argument("--excel-path", required=True)
    load_parser.add_argument("--excel-sheet", required=True)

    login_parser = sub.add_parser("login", help="Start an authenticated Selenium session")
    login_parser.add_argument("--username")
    login_parser.add_argument("--password")

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


def _build_driver() -> Any:
    return webdriver.Chrome()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "load":
        df = load_terms_dataframe(args.excel_path, args.excel_sheet)
        print(f"Loaded {len(df)} rows successfully.")
        return 0

    driver = _build_driver()
    try:
        if args.command == "login":
            username = args.username
            password = args.password
            if not username or not password:
                username, password = prompt_credentials()
            SeleniumSessionManager(driver).login(username, password)
            print("Login submitted.")
            return 0

        if args.command == "create-term":
            creator = AttendanceTermCreator(driver)
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
            result = BulkAttendanceCreator(AttendanceTermCreator(driver)).create_from_excel(
                excel_path=args.excel_path,
                excel_sheet=args.excel_sheet,
                course_code=args.course_code,
            )
            print(json.dumps(result.__dict__, ensure_ascii=False))
            return 0 if result.failed == 0 else 1

        if args.command == "check":
            checker = AttendanceChecker(driver)
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
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
