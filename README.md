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
git clone --branch codex/fix-check-results-and-qr-downloads https://github.com/sjelic/CLASSATT.git
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

## Inline QR images

QR downloading reads exactly one `img` inside each matched attendance row and
saves its `data:image/png;base64,...` contents directly as PNG. It does not open
or click a modal. Rows without images are logged and skipped; rows with multiple
images raise an error rather than selecting an arbitrary image. Filename and
output-directory behavior are unchanged.

## Check every attendance in the Excel calendar

```bash
prisutnosti check-calendar \
  --excel-path ./schedule.xlsx \
  --excel-sheet Sheet1 \
  --course-code B3I3VP \
  --download-list yes \
  --list-directory ./lists \
  --download-qrcode yes \
  --qrcode-directory ./qr
```

This command uses the same workbook validation and columns as bulk creation.
For each row it derives date/time from `ПОЧЕТАК ПРИЈАВЕ` and room from `САЛА`;
`--course-code` applies to all rows. Date, time, and room filters are not entered
manually. Login happens once, and all checks/downloads reuse that authenticated
page. Both download options default to `no`; each enabled download requires its
corresponding directory argument. Every matching attendance is processed by the
existing check functionality, including pagination and downloads.

Found records and missing matches are logged by the checker. A row error is
logged and processing continues with subsequent rows. The final log summary
reports successfully checked rows and failed rows; exit status is 1 if any row
failed, otherwise 0. A successful check with no matches is not a row failure.
No attendance-record collection is returned. The existing single-filter `check`
command remains available.

## Aggregate calendar attendance lists

```bash
prisutnosti check-calendar \
  --excel-path ./schedule.xlsx \
  --excel-sheet Sheet1 \
  --course-code B3I3VP \
  --aggregate-lists yes \
  --list-directory ./lists \
  --aggregate-output-path ./lists/attendance_all.xlsx
```

`--aggregate-lists yes|no` defaults to `no`; `--aggregated-lists` is an alias.
`no` preserves individual-download behavior. `yes` automatically enables list
downloads and requires `--list-directory` and a nonempty `ТИП НАСТАВЕ` column in
the calendar. Individual files are retained. QR download options are unchanged.

Only files downloaded during the current run are combined, immediately after
each download, to associate every student record with the correct calendar row.
Original columns are kept; the added columns are `TIP NASTAVE`, `OD`, `DO`, and
`POČETAK PRIJAVE`. Dates/times are stored as Excel datetime values. Every match
and downloaded list is included; records are not deduplicated across classes.
A merged DataTables report title above the headers is supported. Existing columns
with these metadata names cause an error rather than being overwritten.

The default output is `PRISUTNOST_ZBIRNO_<course-code>.xlsx` under the list
directory. `--aggregate-output-path` overrides it and requires aggregation to be
on. Each run rebuilds the aggregate atomically from current downloads, without
including stale files or a previous aggregate. Calendar and individual-download
files cannot be used as the aggregate output. An empty run produces a workbook
with the calendar metadata columns and no records.

If a download or import fails, that row is logged as failed and later rows are
processed. The aggregate contains the successfully imported lists only, a warning
reports that it is partial, and the command exits with status 1. The final logs
report the output path, number of imported lists, student records, and failed rows.

Agregirana lista uključuje i kolonu `ДАТУМ`, prenetu neposredno iz odgovarajućeg
reda kalendara za svakog studenta. Za agregaciju je zato potrebna kolona `ДАТУМ`
u kalendaru; provera bez agregacije je ne zahteva.
