# Gemini Project Context: WEBCON BPS Data Updater

## Project Overview

This project consists of Python scripts designed to automate the cleaning and updating of project data within a WEBCON BPS database (MS SQL Server). The primary function is to parse composite fields like `Numer projektu` and `Nazwa projektu` to extract and populate more specific fields such as `Numer tematu`, `Kod zadania`, and `Klient (skrót)`.

The project uses `pyodbc` for database connectivity, `python-dotenv` for managing connection credentials, and `rich` for enhanced terminal output.

## Key Files

*   `main.py`: A read-only script for analysis. It fetches and processes data in memory, then displays a report of potential changes in a color-coded table without modifying the database. This is the primary tool for safely previewing the script's logic.
*   `main_updater.py`: The main script for performing database updates. It includes safety features like different execution modes (`test`, `single`, `update-all`).
*   `requirements.txt`: Lists the necessary Python packages (`pyodbc`, `python-dotenv`, `rich`, `ipdb`).
*   `.env` (to be created by user): A critical configuration file for storing database connection details (server, database name, credentials). This file is git-ignored.

## Building and Running

**1. Setup:**

*   Ensure an "ODBC Driver for SQL Server" is installed on the system.
*   Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
*   Create a `.env` file in the root directory to configure the database connection.

    *For Windows Authentication (recommended):*
    ```dotenv
    DB_SERVER=YOUR_SERVER_NAME
    DB_NAME=YOUR_DATABASE_NAME
    DB_USER=
    DB_PASSWORD=
    ```

    *For SQL Server Authentication:*
    ```dotenv
    DB_SERVER=YOUR_SERVER_NAME
    DB_NAME=YOUR_DATABASE_NAME
    DB_USER=your_sql_login
    DB_PASSWORD=your_sql_password
    ```

**2. Execution Modes:**

*   **Analysis (Dry Run):** To see what changes would be made without writing to the database.
    ```bash
    python main.py
    ```
    or
    ```bash
    python main_updater.py 
    ```

*   **Update a Single Record:** To test the database write operation on the first record that needs changes.
    ```bash
    python main_updater.py --single
    ```

*   **Update All Records:** To apply changes to all relevant records in the database. The script will ask for final confirmation before proceeding.
    ```bash
    python main_updater.py --update-all
    ```

## Development Conventions

*   **Database Logic:** The core SQL query is located at the top of both `main.py` and `main_updater.py`. It selects project data from the `WFElements` table where `WFD_DTYPEID = 61`.
*   **Data Parsing:** The logic for splitting `Numer_projektu` (using `_` as a delimiter) and extracting the client abbreviation from `Nazwa_projektu` is handled within the main loop in both scripts.
*   **Debugging:** The project is set up to use `ipdb`. To debug, import `ipdb` and place `ipdb.set_trace()` at the desired breakpoint in the code.
