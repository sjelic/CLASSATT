"""Check each attendance in an Excel calendar using one authenticated page."""
from dataclasses import dataclass
import logging
from pathlib import Path

from .list_aggregator import AttendanceListAggregator

from .checker import AttendanceChecker
from .loader import dataframe_to_terms, load_terms_dataframe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarCheckResult:
    checked: int
    failed: int
    aggregate_path: Path | None = None


class CalendarAttendanceChecker:
    def __init__(self, checker: AttendanceChecker) -> None:
        self.checker = checker

    def check_from_excel(self, *, excel_path: str, excel_sheet: str, course_code: str,
                         download_list: bool = False, list_directory: str | None = None,
                         download_qrcode: bool = False, qrcode_directory: str | None = None,
                         aggregate_lists: bool = False, aggregate_output_path: str | None = None) -> CalendarCheckResult:
        download_list = download_list or aggregate_lists
        if aggregate_output_path and not aggregate_lists:
            raise ValueError("aggregate_output_path requires aggregate_lists=yes")
        if download_list and not list_directory:
            raise ValueError("list_directory is required when downloading attendance lists.")
        if download_qrcode and not qrcode_directory:
            raise ValueError("qrcode_directory is required when downloading QR codes.")
        df = load_terms_dataframe(excel_path, excel_sheet)
        aggregator = None
        if aggregate_lists:
            if "ДАТУМ" not in df.columns:
                raise ValueError("Aggregation requires calendar column ДАТУМ")
            if "ТИП НАСТАВЕ" not in df.columns or df["ТИП НАСТАВЕ"].isna().any() or df["ТИП НАСТАВЕ"].astype(str).str.strip().eq("").any():
                raise ValueError("Aggregation requires ТИП НАСТАВЕ for every calendar row")
            default_name = AttendanceChecker._filename("PRISUTNOST_ZBIRNO", {"Kod predmeta": course_code}, ".xlsx").removesuffix("_UNKNOWN_UNKNOWN_UNKNOWN.xlsx") + ".xlsx"
            output = Path(aggregate_output_path) if aggregate_output_path else Path(list_directory) / default_name
            if output.suffix.lower() != ".xlsx":
                raise ValueError("Aggregate output must have an .xlsx extension")
            if output.resolve() == Path(excel_path).resolve():
                raise ValueError("Aggregate output cannot overwrite the calendar workbook")
            aggregator = AttendanceListAggregator(output)
        terms = dataframe_to_terms(df)
        checked = failed = 0
        for index, term in enumerate(terms, start=1):
            date = term.registration_start.strftime("%Y-%m-%d")
            time = term.registration_start.strftime("%H:%M:%S")
            logger.info("Checking calendar row %d/%d: course=%s date=%s time=%s room=%s",
                        index, len(terms), course_code, date, time, term.room)
            extra = {}
            if aggregator is not None:
                metadata = {"TIP NASTAVE": str(df.iloc[index - 1]["ТИП НАСТАВЕ"]),
                            "OD": term.starts_at, "DO": term.ends_at, "POČETAK PRIJAVE": term.registration_start, "ДАТУМ": df.iloc[index - 1]["ДАТУМ"]}
                extra["on_list_downloaded"] = lambda path, values=metadata: aggregator.add(path, values)
            try:
                self.checker.check(date=date, time=time, course_code=course_code, room=term.room,
                                   download_list=download_list, list_directory=list_directory,
                                   download_qrcode=download_qrcode, qrcode_directory=qrcode_directory, **extra)
                checked += 1
            except Exception as exc:
                failed += 1
                logger.error("Calendar row %d failed: %s", index, exc)
        logger.info("Calendar check complete: total=%d checked=%d failed=%d", len(terms), checked, failed)
        if aggregator is not None:
            if failed:
                logger.warning("Aggregate includes successful downloads only; %d calendar rows failed", failed)
            aggregator.write()
        return CalendarCheckResult(checked, failed, aggregator.output_path if aggregator else None)
