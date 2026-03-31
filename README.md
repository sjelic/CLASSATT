# Prisutnosti (CLASSATT)

Python CLI project for loading attendance schedules from Excel, creating attendance terms in eSalter through Selenium, and checking/download attendance artifacts.

## Features

- Load and validate teaching term rows from Excel (`load` command).
- Log in to eSalter and keep an authenticated Selenium session (`login` command).
- Create one attendance term (`create-term` command).
- Create multiple attendance terms from Excel with per-row error isolation (`create` command).
- Check/filter created terms and optionally download attendance lists and QR codes (`check` command).

## Installation

### 1) Clone and enter the project

```bash
git clone <your-repo-url>
cd CLASSATT
```

### 2) Install package

```bash
python -m pip install .
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

Arguments:

- `--username` (optional)
- `--password` (optional; if missing, input is prompted with hidden characters)

Example:

```bash
prisutnosti login --username my_user
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

- Selenium WebDriver (Chrome) must be available in your environment.
- This project focuses on command orchestration and automation logic; availability and exact DOM behavior depend on eSalter runtime pages.
