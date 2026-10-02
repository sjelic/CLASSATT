import base64
import logging
from unittest.mock import MagicMock

import pytest

from prisutnosti import checker as module, commands, cli
from prisutnosti.checker import AttendanceChecker


@pytest.mark.parametrize("with_lists", [False, True])
def test_check_logs_all_rows_and_downloads_qr_across_pages(monkeypatch, caplog, with_lists):
    caplog.set_level(logging.INFO)
    page = MagicMock()
    current = [0]
    def evaluate(script, *args):
        if 'page.info()' in script:
            return {"pages": 2}
        current[0] = args[0]
    page.evaluate.side_effect = evaluate
    batches = []
    for page_number in range(2):
        rows = MagicMock()
        rows.count.return_value = 2
        entries = []
        for index in range(2):
            row = MagicMock()
            row.locator.return_value.count.return_value = 0
            row.locator.return_value.all_text_contents.return_value = [f"ABC-{page_number}-{index}"]
            entries.append(row)
        rows.nth.side_effect = entries.__getitem__
        batches.append(rows)
    def locator(selector):
        if 'tbody' in selector:
            return batches[current[0]]
        headers = MagicMock()
        headers.all_text_contents.return_value = ["Kod predmeta"]
        return headers
    page.locator.side_effect = locator
    checker = AttendanceChecker(page)
    checker._open_results = MagicMock()
    checker._download_qrcode_if_available = MagicMock()
    checker._download_list = MagicMock()
    assert checker.check(download_qrcode=True, qrcode_directory="qr",
                         download_list=with_lists, list_directory="lists") is None
    assert checker._download_qrcode_if_available.call_count == 4
    assert checker._download_list.call_count == (4 if with_lists else 0)
    assert "ABC-1-1" in caplog.text
    assert "Found 4 matching attendance terms" in caplog.text


def test_multiple_qr_triggers_and_images_are_saved_and_modal_closed(monkeypatch, tmp_path):
    page, row = MagicMock(), MagicMock()
    triggers = MagicMock()
    triggers.count.return_value = 2
    cells = MagicMock()
    cells.count.return_value = 0
    row.locator.side_effect = lambda selector: cells if selector == "td" else triggers
    modal = page.locator.return_value.first
    images = MagicMock()
    images.count.return_value = 2
    image_nodes = [MagicMock(), MagicMock()]
    for image, payload in zip(image_nodes, [b"first", b"second"]):
        image.get_attribute.return_value = "data:image/png;base64," + base64.b64encode(payload).decode()
    images.nth.side_effect = image_nodes.__getitem__
    close = MagicMock()
    modal.locator.side_effect = lambda selector: images if selector == "div.modal-body > img" else close
    expected = MagicMock()
    monkeypatch.setattr(module, "expect", expected)
    AttendanceChecker(page)._download_qrcode_if_available(row, {"Kod predmeta": "ABC"}, str(tmp_path))
    files = list(tmp_path.glob("*.png"))
    assert len(files) == 4
    assert sorted(path.read_bytes() for path in files) == [b"first", b"first", b"second", b"second"]
    assert triggers.nth.call_count == 2
    assert close.first.click.call_count == 2
    assert expected.return_value.to_be_hidden.call_count == 2


def test_check_command_returns_none_and_does_not_serialize_records(monkeypatch):
    operation = MagicMock()
    operation.check.return_value = [{"should_not_be_returned": True}]
    monkeypatch.setattr(commands, "AttendanceChecker", lambda page: operation)
    assert commands.check(MagicMock()) is None


def test_exists_returns_only_boolean():
    page = MagicMock()
    page.evaluate.return_value = {"recordsDisplay": 3}
    operation = AttendanceChecker(page)
    operation._open_results = MagicMock()
    assert operation.exists(date="2026-10-02", time="10:00", course_code="ABC", room="A1") is True


def test_cli_void_check_finishes_without_logging_serialized_result(monkeypatch, caplog):
    monkeypatch.setattr(commands, "check", lambda *args, **kwargs: None)
    assert cli._run_command(cli.build_parser().parse_args(["check"]), MagicMock()) == 0
    assert "null" not in caplog.text
