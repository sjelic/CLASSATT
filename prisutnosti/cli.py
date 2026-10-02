from __future__ import annotations

import logging

import argparse

from playwright.sync_api import Page

from . import commands
from .browser import browser_page
from .session import AUTHENTICATED_SELECTOR, LoginError, PlaywrightSessionManager, prompt_credentials

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prisutnosti", description="Attendance management CLI")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
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


def _dispatch(args: argparse.Namespace, page: Page | None = None) -> commands.CommandResult | None:
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


def _log_result(result: commands.CommandResult) -> int:
    logger.log(logging.INFO if result.exit_code == 0 else logging.ERROR, "%s", result.output)
    return result.exit_code


def _run_command(args: argparse.Namespace, page: Page | None = None) -> int:
    logger.info("Starting command: %s", args.command)
    try:
        result = _dispatch(args, page)
    except Exception as exc:
        logger.error("Command %s failed (%s)", args.command, type(exc).__name__)
        raise
    code = _log_result(result) if result is not None else 0
    logger.info("Command %s finished with exit status %d", args.command, code)
    return code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("prisutnosti").setLevel(args.log_level)
    if args.command == "load":
        return _run_command(args)

    try:
        username, password = prompt_credentials()
    except ValueError as exc:
        logger.error("Login failed: %s", exc)
        return 1
    with browser_page() as page:
        try:
            PlaywrightSessionManager(page).login(
                username, password, success_selector=AUTHENTICATED_SELECTOR,
            )
        except LoginError as exc:
            logger.error("%s", exc)
            return 1
        return _run_command(args, page)


if __name__ == "__main__":
    raise SystemExit(main())
