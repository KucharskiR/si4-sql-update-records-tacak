# AGENTS.md — WEBCON BPS Data Updater

## Project Overview

Python scripts for analyzing and updating data in a WEBCON BPS database (MS SQL Server).
Each script follows a **dry-run by default** pattern — destructive writes require explicit flags
(`--update`, `--update-all`, `--single`) and user confirmation prompts.

The codebase is written in **Polish** (comments, docstrings, CLI messages, variable names).

## Tech Stack

- **Python 3.6+** (no type hints, no dataclasses — keep it simple)
- **pyodbc** — ODBC connection to SQL Server
- **python-dotenv** — `.env` file for DB credentials
- **rich** — colored terminal output (Console, Table, Progress)
- **ipdb** — interactive debugger (dev dependency)
- **Conda** — environment manager (`c:\Users\RadoslawKucharski\miniconda3\envs`)

## Build / Run / Test Commands

```bash
# Install dependencies (use conda env, NOT system pip)
pip install -r requirements.txt

# --- Main scripts (all default to dry-run / read-only) ---

# Read-only analysis of project data
python main.py
python main.py --only-missing          # show only records with empty fields

# Project data updater (dry-run by default)
python main_updater.py                 # dry-run
python main_updater.py --single        # update first matching record only
python main_updater.py --update-all    # update all (asks confirmation)

# RCP (time tracking) updater
python rcp_updater.py --start-date DD.MM.RRRR --end-date DD.MM.RRRR            # dry-run
python rcp_updater.py --start-date DD.MM.RRRR --end-date DD.MM.RRRR --update   # live update

# One-off updaters (dry-run by default)
python lpp_b1_updater.py               # dry-run
python lpp_b1_updater.py --update      # live update
python pan_kaj_updater.py --update
python kaj_dek_updater.py --update
```

There are **no automated tests** in this project. Verification is done via dry-run mode.

## Project Structure

```
├── main.py                 # Read-only project data viewer
├── main_updater.py         # Project data updater (WFElements, DTYPEID=61)
├── rcp_updater.py          # RCP entries updater (WFElements, DTYPEID=56)
├── lpp_b1_updater.py       # One-off: append "1" to LPP hala B names
├── pan_kaj_updater.py      # One-off: rename PAN → KAJ in project names
├── kaj_dek_updater.py      # One-off: rename KAJ → DEK in project names
├── requirements.txt        # Python dependencies
├── .env                    # DB credentials (git-ignored, user-created)
├── sql/
│   └── sql_kontrahenci.sql # Reference SQL query for contractors
├── resources/
│   ├── get_employee_unit.sql       # Complex CTE to find employee's org unit
│   ├── get_employee_unit_code.sql  # Complex CTE to find employee's unit code
│   ├── wpisy_RCP.txt               # Reference data
│   ├── laczny_czas.txt             # Reference data
│   └── gemini-cli-prompt.md        # Gemini context prompt
└── dane_kontrahenci/       # Reference markdown exports from DB
```

## Code Style & Conventions

### Language
- All comments, docstrings, CLI output, and variable names are in **Polish**.
- Keep new code in Polish to match existing conventions.

### Imports
Standard order (no blank lines between groups — project doesn't enforce it):
```python
import os
import pyodbc
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from datetime import datetime
```

### Naming
- **Functions**: `snake_case` — e.g., `get_connection_string()`, `fetch_data_to_update()`
- **Constants**: `UPPER_SNAKE_CASE` — e.g., `DB_SERVER`, `SQL_QUERY`
- **Variables**: `snake_case` — e.g., `records_to_change`, `updated_count`
- **No classes** — all scripts are procedural with standalone functions

### Function Structure
- Every function has a **Polish docstring** (one-liner in triple quotes).
- Functions are short and focused on a single responsibility.

### Database Connection Pattern
Every script follows this exact pattern:
```python
load_dotenv()
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection_string():
    """Tworzy connection string w zależności od metody uwierzytelniania."""
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=...;UID={DB_USER};PWD={DB_PASSWORD};"
    else:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=...;Trusted_Connection=yes;"
```

### SQL Queries
- Inline SQL as module-level `SQL_QUERY` constant for simple queries.
- Complex SQL stored in `resources/*.sql` files, loaded via `get_sql_from_file()`.
- **Always use parameterized queries** (`?` placeholders) — never string interpolation for values.
- SQL template variables from WEBCON (`#{VarName}#`) are replaced with `?` at runtime.

### Error Handling
```python
connection = None
try:
    # ... database operations ...
except pyodbc.Error as ex:
    sqlstate = ex.args[0]
    console.print(f"Błąd połączenia z bazą danych: {sqlstate}", style="bold red")
    if connection:
        connection.rollback()
except Exception as e:
    console.print(f"Wystąpił nieoczekiwany błąd: {e}", style="bold red")
finally:
    if connection:
        connection.close()
        console.print("\nPołączenie z bazą danych zostało zamknięte.", style="bold blue")
```

### CLI Pattern (argparse)
- Every script uses `argparse` with `RawTextHelpFormatter`.
- Destructive operations require explicit flags AND user confirmation.
- Default mode is always **test/dry-run** (safe by default).

### Output with Rich
- Use `console.print()` with Rich markup — not `print()`.
- Use `rich.table.Table` for tabular data display.
- Use `rich.progress.Progress` for long-running operations.
- Color scheme: blue=info, yellow=warning, red=error, green=success, magenta=headers.

### WEBCON BPS Data Notes
- `WFElements` table stores workflow items; `WFD_DTYPEID` identifies the process type.
- `WFElementDetails` stores sub-items (line items / detail rows).
- Choice fields store values as `InternalName#DisplayName` (e.g., `3747_22#LPP_Name`).
- `dbo.ClearWFElem()` is a WEBCON SQL function that extracts the display value from choice fields.
- `dbo.ClearWFElemID()` extracts the internal ID from choice fields.

## Critical Rules

1. **NEVER run UPDATE queries without explicit user request** — always default to dry-run.
2. **NEVER commit .env** — it contains database credentials and is git-ignored.
3. **Always use parameterized SQL queries** — prevent SQL injection.
4. **Always rollback on error** when a connection exists.
5. **Always close connections** in the `finally` block.
6. **Match existing Polish language** for all user-facing text and comments.
7. **Preserve the dry-run pattern** — new scripts must be safe-by-default.

## Debugging

```python
import ipdb
ipdb.set_trace()  # place at desired breakpoint
```
