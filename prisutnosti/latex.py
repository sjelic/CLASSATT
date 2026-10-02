"""Generate a complete attendance QR booklet from the bulk attendance workbook."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from importlib.resources import files
import logging
from pathlib import Path
import tempfile

import pandas as pd

from .checker import AttendanceChecker
from .loader import load_terms_dataframe

logger = logging.getLogger(__name__)
MONTHS = ("januar", "februar", "mart", "april", "maj", "jun", "jul", "avgust",
          "septembar", "oktobar", "novembar", "decembar")
ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
           "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
           "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


@dataclass(frozen=True)
class LatexResult:
    output_path: Path
    written: int
    skipped: tuple[Path, ...]


def _escape(value: str) -> str:
    return "".join(ESCAPES.get(ch, ch) for ch in value)


def _room(value: object) -> str:
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def _path_text(value: str) -> str:
    # These characters cannot safely occur in a TeX detokenize argument.
    if any(ch in value for ch in "%{}\n\r"):
        raise ValueError("LaTeX image paths cannot contain %, braces, or line breaks.")
    return value


def generate_latex(*, excel_path: str, excel_sheet: str, course_code: str,
                   qrcode_directory: str, output_path: str) -> LatexResult:
    df = load_terms_dataframe(excel_path, excel_sheet)
    if "ТИП НАСТАВЕ" not in df.columns:
        raise ValueError("Missing required column: ТИП НАСТАВЕ")
    image_dir = Path(qrcode_directory).resolve()
    destination = Path(output_path).resolve()
    if destination.suffix.lower() != ".tex":
        raise ValueError("output_path must have a .tex extension")
    if destination == Path(excel_path).resolve():
        raise ValueError("Output must not overwrite the source workbook")
    image_path = _path_text(image_dir.as_posix().rstrip("/") + "/")
    records = []
    for index, row in df.iterrows():
        kind = row["ТИП НАСТАВЕ"]
        if pd.isna(kind) or not str(kind).strip() or pd.isna(row["САЛА"]):
            raise ValueError(f"Empty teaching type or room at Excel row {index + 2}")
        registration, start, end = [pd.to_datetime(row[key]) for key in ("ПОЧЕТАК ПРИЈАВЕ", "ОД", "ДО")]
        if any(pd.isna(value) for value in (registration, start, end)):
            raise ValueError(f"Invalid date/time at Excel row {index + 2}")
        records.append((registration, start, end, str(kind).strip(), _room(row["САЛА"])))
    # Stable chronological ordering; group classes by registration day and type.
    groups = {}
    for record in sorted(records, key=lambda entry: (entry[0], entry[1])):
        groups.setdefault((record[0].date(), record[3]), []).append(record)
    session_counts, class_counts = defaultdict(int), defaultdict(int)
    pages, skipped = [], []
    for (_, kind), group in groups.items():
        session_counts[kind] += 1
        for registration, start, end, _, room in group:
            class_counts[kind] += 1
            filename = AttendanceChecker._filename("QRCODE", {
                "Kod predmeta": course_code, "Datum prisustva": registration.strftime("%Y-%m-%d"),
                "Vreme pocetka": registration.strftime("%H:%M:%S"), "Sala": room,
            }, ".png")
            final_path = image_dir / filename
            if not final_path.is_file():
                skipped.append(final_path)
                logger.warning("Skipping missing QR code: %s", final_path)
                continue
            _path_text(filename)
            date_text = f"{registration.day}. {MONTHS[registration.month - 1]} {registration.year}."
            heading = _escape(f"{session_counts[kind]}. {kind}: {date_text} Sala: {room}")
            subheading = _escape(f"{class_counts[kind]}. čas, {start:%H:%M} - {end:%H:%M}")
            pages.append(
                "\\newpage\n"
                f"\\sectionaddtoc{{{heading}}}\n"
                f"\\subsectionaddtoc{{{subheading}}}\n"
                "\\vspace{3cm}\n\\begin{center}\n"
                f"\\includegraphics[width=0.85\\textwidth]{{\\detokenize{{{filename}}}}}\n"
                "\\end{center}\n"
            )
            logger.info("Adding QR page: %s", filename)
    template = files("prisutnosti").joinpath("templates/attendance.tex").read_text(encoding="utf-8")
    content = template.replace("@@IMG_PATH@@", image_path).replace("@@PAGES@@", "\n".join(pages))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=destination.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    logger.info("LaTeX rebuilt: %s; included=%d skipped=%d", destination, len(pages), len(skipped))
    return LatexResult(destination, len(pages), tuple(skipped))
