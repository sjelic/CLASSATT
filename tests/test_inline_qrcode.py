import base64
from unittest.mock import MagicMock

import pytest

from prisutnosti.checker import AttendanceChecker


def test_download_reads_only_the_supplied_row_and_writes_decoded_bytes(tmp_path):
    page, row = MagicMock(), MagicMock()
    img = row.locator.return_value
    img.count.return_value = 1
    payload = b"\x89PNG\r\n\x1a\nexample"
    img.get_attribute.return_value = "data:image/png;base64," + base64.b64encode(payload).decode()
    record = {"Kod predmeta": "ABC", "Datum prisustva": "2026-10-02", "Vreme pocetka": "10:00", "Sala": "A1"}
    result = AttendanceChecker(page)._download_qrcode_if_available(row, record, str(tmp_path))
    assert result is None
    row.locator.assert_called_once_with("img")
    page.locator.assert_not_called()
    img.click.assert_not_called()
    assert (tmp_path / "QRCODE_ABC_2026-10-02_10_00_A1.png").read_bytes() == payload


@pytest.mark.parametrize("count", [2, 3])
def test_ambiguous_row_images_raise_without_writing(tmp_path, count):
    row = MagicMock()
    row.locator.return_value.count.return_value = count
    with pytest.raises(ValueError, match="Expected exactly one"):
        AttendanceChecker(MagicMock())._download_qrcode_if_available(row, {}, str(tmp_path))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("count,src", [(0, None), (1, None), (1, "https://example.com/image.png")])
def test_missing_or_unsupported_image_does_not_write(tmp_path, count, src):
    row = MagicMock()
    row.locator.return_value.count.return_value = count
    row.locator.return_value.get_attribute.return_value = src
    assert AttendanceChecker(MagicMock())._download_qrcode_if_available(row, {}, str(tmp_path)) is None
    assert not list(tmp_path.iterdir())
