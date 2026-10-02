from __future__ import annotations

import argparse
import sys

from playwright.sync_api import Page

from . import commands
from .browser import browser_page
from .session import AUTHENTICATED_SELECTOR, LoginError, PlaywrightSessionManager, prompt_credentials


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


def _dispatch(args: argparse.Namespace, page: Page | None = None) -> commands.CommandResult:
    """Translate CLI parameters into operation parameters without browser policy."""
    if args.command == "load":
        return commands.load(excel_path=args.excel_path, excel_sheet=args.excel_sheet)
    if args.command == "login":
        return commands.login()
    if page is None:
        raise ValueError("This command requires an authenticated browser page.")
    if args.command == "create-term":
        return commands.create_term(
            page, date=args.date, time=args.time, link_duration=args.link_duration,
            course_code=args.course_code, activation=args.activation, room=args.room,
        )
    if args.command == "create":
        return commands.create(
            page, excel_path=args.excel_path, excel_sheet=args.excel_sheet, course_code=args.course_code,
        )
    if args.command == "check":
        return commands.check(
            page, date=args.date, time=args.time, course_code=args.course_code, room=args.room,
            download_list=args.download_list == "yes", list_directory=args.list_directory,
            download_qrcode=args.download_qrcode == "yes", qrcode_directory=args.qrcode_directory,
        )
    raise ValueError(f"Unknown command: {args.command}")


def _print_result(result: commands.CommandResult) -> int:
    print(result.output)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "load":
        return _print_result(_dispatch(args))

    try:
        username, password = prompt_credentials()
    except ValueError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1
    with browser_page() as page:
        try:
            PlaywrightSessionManager(page).login(
                username, password, success_selector=AUTHENTICATED_SELECTOR,
            )
        except LoginError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return _print_result(_dispatch(args, page))


if __name__ == "__main__":
    raise SystemExit(main())
