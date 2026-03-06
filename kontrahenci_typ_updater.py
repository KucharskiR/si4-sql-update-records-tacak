import os
import pyodbc
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import argparse

# Załadowanie zmiennych środowiskowych
load_dotenv()

# Inicjalizacja konsoli
console = Console()

# Konfiguracja bazy danych
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Ścieżka do pliku SQL z zapytaniem pobierającym kontrahentów z bazy
SQL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql", "sql_kontrahenci.sql")

# Wartość do zamiany
OLD_VALUE = "NEWDIC/f735d189-8ba1-470f-8254-dc3280e490f2#pusty"
NEW_VALUE = "f735d189-8ba1-470f-8254-dc3280e490f2#----"

# Kolumna bazy danych — TypKontrahenta
DB_COLUMN = "WFD_AttChoose3"


def get_connection_string():
    """Tworzy connection string w zależności od metody uwierzytelniania."""
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;"
    else:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;TrustServerCertificate=yes;"


def get_sql_from_file(file_path):
    """Wczytuje zapytanie SQL z pliku."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def update_record(cursor, wfd_signature, new_value):
    """Aktualizuje TypKontrahenta w tabeli WFElements po WFD_Signature."""
    cursor.execute(
        f"UPDATE WFElements SET {DB_COLUMN} = ? WHERE WFD_Signature = ?",
        new_value,
        wfd_signature
    )


def process_typ_kontrahenta(mode='test'):
    """Znajduje kontrahentów z TypKontrahenta = 'pusty' i zamienia na '----'."""
    connection = None
    updated_count = 0
    records_to_change = []

    try:
        # 1. Wczytanie zapytania SQL
        if not os.path.exists(SQL_FILE_PATH):
            console.print(f"Nie znaleziono pliku SQL: {SQL_FILE_PATH}", style="bold red")
            return

        sql_query = get_sql_from_file(SQL_FILE_PATH)

        # 2. Połączenie z bazą i pobranie kontrahentów
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        console.print("Pobieranie kontrahentów z bazy danych...", style="bold blue")
        cursor.execute(sql_query)
        db_rows = cursor.fetchall()

        if not db_rows:
            console.print("Nie znaleziono żadnych kontrahentów w bazie danych.", style="bold red")
            return

        console.print(f"Pobrano {len(db_rows)} kontrahentów z bazy danych.", style="bold blue")

        # 3. Filtrowanie rekordów z TypKontrahenta = OLD_VALUE
        with Progress() as progress:
            task = progress.add_task("Wyszukiwanie rekordów do aktualizacji...", total=len(db_rows))

            for db_row in db_rows:
                progress.advance(task)

                typ_kontrahenta = getattr(db_row, "TypKontrahenta", None) or ""
                if typ_kontrahenta == OLD_VALUE:
                    records_to_change.append({
                        "wfd_signature": db_row.WFD_Signature,
                        "nazwa": db_row.NazwaKontrahenta or "",
                        "nip": db_row.NIP or "",
                    })

        if not records_to_change:
            console.print("Nie znaleziono kontrahentów z TypKontrahenta = 'pusty'.", style="bold yellow")
            return

        console.print(f"Znaleziono {len(records_to_change)} rekordów do aktualizacji.\n", style="bold green")

        # 4. Aktualizacja i wyświetlenie raportu
        table = Table(title="Raport aktualizacji TypKontrahenta ('pusty' -> '----')", show_header=True, header_style="bold magenta")
        table.add_column("Sygnatura", style="dim", width=15)
        table.add_column("Nazwa kontrahenta", width=50)
        table.add_column("NIP", width=18)
        table.add_column("Status", style="yellow", width=20)

        if mode in ('update', 'single'):
            limit = 30 if mode == 'single' else len(records_to_change)
            with Progress() as update_progress:
                update_task = update_progress.add_task("Aktualizacja rekordów...", total=limit)
                for record in records_to_change:
                    try:
                        update_record(cursor, record["wfd_signature"], NEW_VALUE)
                        update_status = "[bold green]Zaktualizowano[/bold green]"
                        updated_count += 1
                    except Exception as e:
                        update_status = f"[bold red]Błąd: {e}[/bold red]"

                    update_progress.advance(update_task)

                    table.add_row(
                        str(record["wfd_signature"]),
                        record["nazwa"],
                        record["nip"],
                        update_status
                    )

                    if mode == 'single' and updated_count >= 30:
                        break
        else:
            for record in records_to_change:
                table.add_row(
                    str(record["wfd_signature"]),
                    record["nazwa"],
                    record["nip"],
                    "Oczekuje (tryb testowy)"
                )

        console.print(table)

        if mode == 'update':
            connection.commit()
            console.print(f"Zakończono. Zaktualizowano {updated_count} rekordów.", style="bold green")
        elif mode == 'single':
            connection.commit()
            console.print(f"Tryb testowy (single). Zaktualizowano {updated_count} z maks. 30 rekordów.", style="bold green")
        else:
            console.print(f"Tryb testowy zakończony. {len(records_to_change)} rekordów zostałoby zaktualizowanych.", style="bold yellow")

    except pyodbc.Error as ex:
        console.print(f"Błąd bazy danych. SQLSTATE: {ex.args[0]}", style="bold red")
        console.print(f"Pełny komunikat błędu: {ex}", style="bold red")
        if connection:
            connection.rollback()
    except Exception as e:
        console.print(f"Wystąpił nieoczekiwany błąd w skrypcie: {e}", style="bold red")
    finally:
        if connection:
            connection.close()
            console.print("\nPołączenie z bazą danych zostało zamknięte.", style="bold blue")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Zamienia TypKontrahenta z 'pusty' na '----' w WEBCON BPS.\n\n"
                    "Szuka rekordów z wartością: f735d189-8ba1-470f-8254-dc3280e490f2#pusty\n"
                    "Zamienia na: f735d189-8ba1-470f-8254-dc3280e490f2#----\n\n"
                    "Domyślnie działa w trybie testowym (dry-run) — nie wprowadza zmian w bazie.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--single",
        action="store_true",
        help="Aktualizuj tylko pierwsze 30 pasujących rekordów (do testów zapisu)."
    )
    mode_group.add_argument(
        "--update",
        action="store_true",
        help="Aktualizuj WSZYSTKIE pasujące rekordy w bazie danych."
    )

    args = parser.parse_args()

    mode = 'test'
    if args.single:
        mode = 'single'
        console.print("UWAGA: Ta operacja zaktualizuje do 30 rekordów kontrahentów w bazie danych.", style="bold yellow")
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != 'tak':
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()
    elif args.update:
        mode = 'update'
        console.print("UWAGA: Ta operacja zaktualizuje WSZYSTKIE pasujące rekordy kontrahentów w bazie danych.", style="bold yellow")
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != 'tak':
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()

    process_typ_kontrahenta(mode=mode)
