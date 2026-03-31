from __future__ import annotations

import pandas as pd

from prisutnosti import cli


def test_cli_load_command(tmp_path, capsys) -> None:
    excel = tmp_path / "terms.xlsx"
    df = pd.DataFrame(
        {
            "ОД": ["2026-04-01 10:00:00"],
            "ДО": ["2026-04-01 11:00:00"],
            "САЛА": ["A1"],
            "ПОЧЕТАК ПРИЈАВЕ": ["2026-04-01 10:05:00"],
            "ТРАЈАЊЕ ЛИНКА": [30],
            "АКТИВАЦИЈА": ["selected"],
        }
    )
    df.to_excel(excel, sheet_name="Data", index=False)

    rc = cli.main(["load", "--excel-path", str(excel), "--excel-sheet", "Data"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Loaded 1 rows successfully." in out
