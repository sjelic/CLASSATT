import logging
from pathlib import Path

import pandas as pd
import pytest

from prisutnosti.latex import generate_latex
from prisutnosti import cli


def workbook(tmp_path, types=("PREDAVANJE", "PREDAVANJE", "VEŽBE", "PREDAVANJE", "PREDAVANJE")):
    dates = ["2026-10-08 13:15:00", "2026-10-08 14:15:00", "2026-10-08 15:15:00",
             "2026-10-09 13:15:00", "2026-11-05 13:15:00"]
    rows = []
    for date, kind in zip(dates, types):
        start = pd.Timestamp(date)
        rows.append({"ОД": start, "ДО": start + pd.Timedelta(hours=1), "САЛА": 322,
                     "ПОЧЕТАК ПРИЈАВЕ": start, "ТРАЈАЊЕ ЛИНКА": 30,
                     "АКТИВАЦИЈА": "selected", "ТИП НАСТАВЕ": kind})
    excel = tmp_path / "calendar.xlsx"
    pd.DataFrame(rows[::-1]).to_excel(excel, sheet_name="Calendar", index=False)
    images = tmp_path / "QR images"
    images.mkdir()
    for date in [dates[0], dates[1], dates[2], dates[4]]:
        name = f"QRCODE_B3I3VP_{pd.Timestamp(date):%Y-%m-%d_%H_%M_%S}_322.png"
        (images / name).write_bytes(b"test image")
    return dict(excel_path=str(excel), excel_sheet="Calendar", course_code="B3I3VP",
                qrcode_directory_path=str(tmp_path), qrcode_subfolder_path="QR images", output_path=str(tmp_path / "booklet.tex"))


def test_booklet_rebuilds_idempotently_and_keeps_calendar_counters(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    options = workbook(tmp_path)
    result = generate_latex(**options)
    content = result.output_path.read_text()
    assert result.written == 4
    assert r"\graphicspath{{\detokenize{QR images/}}}" in content
    assert str(tmp_path) not in content
    assert len(result.skipped) == 1
    assert result.skipped[0].name == "QRCODE_B3I3VP_2026-10-09_13_15_00_322.png"
    assert content.count("\\includegraphics[") == 4
    assert content.count("\\newpage") == 4
    assert content.count("\\sectionaddtoc{") == 3
    assert content.count("\\subsectionaddtoc{") == 4
    assert "1. PREDAVANJE: 8. oktobar 2026. Sala: 322" in content
    assert "1. VEŽBE: 8. oktobar 2026. Sala: 322" in content
    assert "3. PREDAVANJE: 5. novembar 2026. Sala: 322" in content
    assert "4. čas, 13:15 - 14:15" in content
    assert str(result.skipped[0]) in caplog.text
    original = result.output_path.read_bytes()
    assert generate_latex(**options).output_path.read_bytes() == original
    # Removing all images rebuilds the complete file without stale pages.
    for image in (Path(options["qrcode_directory_path"]) / options["qrcode_subfolder_path"]).glob("*.png"):
        image.unlink()
    result = generate_latex(**options)
    assert result.written == 0 and len(result.skipped) == 5
    assert "\\includegraphics[" not in result.output_path.read_text()


def test_required_type_column_and_empty_types_preserve_previous_output(tmp_path):
    options = workbook(tmp_path)
    output = Path(options["output_path"])
    output.write_text("previous")
    df = pd.read_excel(options["excel_path"])
    df.drop(columns=["ТИП НАСТАВЕ"]).to_excel(options["excel_path"], sheet_name="Calendar", index=False)
    with pytest.raises(ValueError, match="ТИП НАСТАВЕ"):
        generate_latex(**options)
    assert output.read_text() == "previous"


def test_latex_escapes_teaching_type(tmp_path):
    options = workbook(tmp_path, types=("PRED_&%",) * 5)
    content = generate_latex(**options).output_path.read_text()
    assert r"PRED\_\&\%" in content


def test_cli_generates_without_login_and_reports_skipped_files(tmp_path, monkeypatch, caplog):
    options = workbook(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("LaTeX generation must not start browser/login")
    monkeypatch.setattr(cli, "prompt_credentials", forbidden)
    monkeypatch.setattr(cli, "browser_page", forbidden)
    arguments = ["latex"]
    for name, value in options.items():
        arguments.extend(["--" + name.replace("_", "-"), value])
    assert cli.main(arguments) == 0
    assert "included=4; skipped=1" in caplog.text
    assert "Skipped QR codes:" in caplog.text


def test_section_precedes_first_available_subsection_when_first_qr_is_missing(tmp_path):
    options = workbook(tmp_path)
    ((Path(options["qrcode_directory_path"]) / options["qrcode_subfolder_path"]) / "QRCODE_B3I3VP_2026-10-08_13_15_00_322.png").unlink()
    result = generate_latex(**options)
    content = result.output_path.read_text()
    assert result.written == 3
    assert content.count("\\sectionaddtoc{") == 3
    assert "\\sectionaddtoc{1. PREDAVANJE: 8. oktobar 2026. Sala: 322}\n\\subsectionaddtoc{2. čas" in content


def test_absolute_subfolder_is_rejected(tmp_path):
    options = workbook(tmp_path)
    options["qrcode_subfolder_path"] = str(tmp_path / "QR images")
    with pytest.raises(ValueError, match="must be relative"):
        generate_latex(**options)
