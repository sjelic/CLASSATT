# Prisutnosti (CLASSATT)

Python CLI project for loading attendance schedules from Excel, creating attendance terms in eSalter through Playwright, and checking/download attendance artifacts.

## Features

- Load and validate teaching term rows from Excel (`load` command).
- Verify eSalter login (`login` command); authenticate automatically before each browser operation.
- Create one attendance term (`create-term` command).
- Create multiple attendance terms from Excel with per-row error isolation (`create` command).
- Check/filter created terms and optionally download attendance lists and QR codes (`check` command).

## Installation

### 1) Clone and enter the project

```bash
git clone --branch codex/generate-attendance-latex https://github.com/sjelic/CLASSATT.git
cd CLASSATT
```

### 2) Install package

```bash
python -m pip install .
```

Install Microsoft Edge if it is not already installed:

```bash
python -m playwright install msedge
```

### 3) Install developer dependencies (tests)

```bash
python -m pip install -e .[dev]
```

## Command reference

The CLI executable is:

```bash
prisutnosti
```

### `prisutnosti load`
Load an Excel sheet into a Pandas DataFrame and validate required columns/business rules.

Arguments:

- `--excel-path` (required): path to the Excel file.
- `--excel-sheet` (required): sheet name containing the table.

Required columns in the sheet:

- `ОД`
- `ДО`
- `САЛА`
- `ПОЧЕТАК ПРИЈАВЕ`
- `ТРАЈАЊЕ ЛИНКА`
- `АКТИВАЦИЈА`

Validation rules:

1. `ПОЧЕТАК ПРИЈАВЕ + ТРАЈАЊЕ ЛИНКА` must be inside `[ОД, ДО]`.
2. `ОД < ДО` (including date part sanity).

Example:

```bash
prisutnosti load --excel-path ./schedule.xlsx --excel-sheet Sheet1
```

### `prisutnosti login`
Open login page and submit credentials to eSalter.

Every browser command (`login`, `create-term`, `create`, and `check`) prompts for
username/email and password. Password input is hidden. Credentials are neither
read from environment variables nor saved. The same authenticated browser context
is used for the entire command and closed afterwards. `login` verifies access and exits;
it does not save a session for later commands.

The login uses username `id="kime"` / `name="kime"` and password
`id="lozinka"` / `name="lozinka"`. This eSalter version has no human check.
Login opens the sign-in link from the teacher homepage and submits with
`id="btnSubMitc"`. It verifies `#navbarDropdownPortfolio` on the resulting page;
login does not navigate to an attendance page. Each operation owns its navigation:
creation opens `https://esalter.grf.bg.ac.rs/nastavnik/form_kreiraj_prisustvo.php`,
and checking opens the attendance overview. A failed or unverifiable login prints
an error, closes Edge, and exits with status 1 without performing attendance actions.
`load` requires no login.
All attendance and Excel options remain command-line parameters.

```bash
prisutnosti login
```

### `prisutnosti create-term`
Create a single attendance term.

Arguments:

- `--date` (required), format: `YYYY-MM-DD`
- `--time` (required), format: `HH:MM:SS`
- `--link-duration` (required), minutes
- `--course-code` (required), course code value
- `--activation` (required), `selected` or `ne`
- `--room` (required), room value

Example:

```bash
prisutnosti create-term \
  --date 2026-04-01 \
  --time 10:00:00 \
  --link-duration 30 \
  --course-code MAT101 \
  --activation selected \
  --room A1
```

### `prisutnosti create`
Create attendance terms from Excel, row by row.

Arguments:

- `--excel-path` (required)
- `--excel-sheet` (required)
- `--course-code` (required)

Behavior:

- Reuses the loader module for reading/validation.
- Calls single-term creator iteratively.
- If one row fails, processing continues.
- Prints JSON summary with `created`, `failed`, `errors`.

Example:

```bash
prisutnosti create --excel-path ./schedule.xlsx --excel-sheet Sheet1 --course-code MAT101
```

### `prisutnosti check`
Filter and inspect created terms.

Arguments (all optional):

- `--date` (`YYYY-MM-DD`)
- `--time` (`HH:MM:SS`)
- `--course-code`
- `--room`
- `--download-list` (`yes|no`)
- `--list-directory`
- `--download-qrcode` (`yes|no`)
- `--qrcode-directory`

Search term is built from provided parts only (date/code/room/time).

Example:

```bash
prisutnosti check --date 2026-04-01 --course-code MAT101 --download-qrcode yes --qrcode-directory ./qr
```

## Running tests

```bash
pytest
```

## Notes

- Microsoft Edge is launched visibly through Playwright (`channel="msedge"`); no WebDriver is required.
- Downloads require the corresponding directory parameter; attendance exports are saved from actual browser downloads.
- Attendance tables are expected to use the existing jQuery DataTables pagination.
- This project focuses on command orchestration and automation logic; availability and exact DOM behavior depend on eSalter runtime pages.

## Code organization

- `cli.py`: argument parsing, authentication before dispatch, logging, and exit status.
- `commands.py`: typed command parameters and operation results, independent of argparse.
- `browser.py`: Edge startup and cleanup for the lifetime of a command.
- `session.py`: login submission and authentication verification; no landing-page parameter.
- `single_creator.py`, `bulk_creator.py`, `checker.py`, `loader.py`: existing operation logic and navigation.

## Existing attendance detection

Before submitting a single or bulk attendance, the creator searches using the
existing checker with the same date, time, course code, and room. A match skips
creation and reports that the attendance already exists. Search failures stop
single creation; bulk creation records the row failure and continues.

Bulk creation processes every row and its JSON summary includes `created`,
`skipped`, `failed`, and `errors`. Skipped rows count as successful processing
(exit status 0 when there are no failures). Newly created attendance is still
verified through the checker after submission. CLI date strings are converted to
date objects before using the calendar picker.

## Generate a LaTeX QR booklet

Use the same workbook and sheet as bulk attendance creation, with the additional
required column `ТИП НАСТАВЕ` (for example `PREDAVANJE`, `VEŽBE`, `KOLOKVIJUM`).
This command is local and does not prompt for credentials or launch Edge:

```bash
prisutnosti latex \
  --excel-path ./schedule.xlsx \
  --excel-sheet Sheet1 \
  --course-code B3I3VP \
  --qrcode-directory ./qr \
  --output-path ./attendance.tex
```

The command always rebuilds the complete UTF-8 `.tex` file, never appends, and
replaces it only after successful generation. Existing output survives input
validation errors. Each existing QR image gets one page after the table of
contents. Missing QR files produce warnings and a final summary listing every
skipped path; generation still succeeds with exit code 0.

Rows are ordered chronologically and grouped by the registration date from
`ПОЧЕТАК ПРИЈАВЕ` and `ТИП НАСТАВЕ`. Each type has its own daily-session counter
(one increment per date/type group) and its own continuous class counter across
dates. Counters include skipped rows, preserving the calendar's numbering.
Rooms come from `САЛА`; class start/end times come from `ОД`/`ДО` in `HH:MM`.
Serbian dates use month names such as `5. novembar 2025.`. Teaching-type values
are used as written in Excel.

Expected filenames use registration date/time, including seconds:
`QRCODE_B3I3VP_2026-10-08_13_15_00_322.png`. Image paths are resolved and checked
before rendering. QR naming uses the same filename helper as QR downloads.
LaTeX-sensitive heading text is escaped.

The bundled template follows the supplied page layout. Cyrillic support uses
XeLaTeX or LuaLaTeX with the DejaVu Serif font. `structure.tex` and `commands.tex`
are included if present in the LaTeX working directory. `linktoc=all` replaces
the template's unsupported `linktoc=subsection` option. Compile twice from the
output directory to populate the table of contents:

```bash
xelatex attendance.tex
xelatex attendance.tex
```

No PDF compilation is performed by the CLI. Paths containing `%`, braces, or
line breaks are rejected because they cannot safely be used in the image macros.

Each registration-date/teaching-type group has one section heading, immediately
before its first available QR subsection. Later classes get subsections and new
pages without repeating the section. Groups with no QR files have no heading.
