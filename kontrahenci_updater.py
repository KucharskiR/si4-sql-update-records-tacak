import os
import csv
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

# Ścieżka do pliku CSV z danymi kontrahentów
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dane_kontrahenci", "kontrahenci_mapped_PROD.csv")

# Ścieżka do pliku SQL z zapytaniem pobierającym kontrahentów z bazy
SQL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql", "sql_kontrahenci.sql")

# Mapowanie kolumn CSV na kolumny bazy danych (WFElements)
# CSV kolumna -> DB kolumna
CSV_TO_DB_MAPPING = {
    "Grupa firm": "WFD_AttChoose12",
    "Branża": "WFD_AttChoose4",
    "Profil kontrahenta": "WFD_AttChoose2",
    "Typ kontrahenta": "WFD_AttChoose3",
}


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


def normalize_nip(nip):
    """Normalizuje NIP — usuwa prefiks 'PL' i białe znaki."""
    if not nip:
        return ""
    nip = nip.strip()
    if nip.upper().startswith("PL"):
        nip = nip[2:]
    return nip


def load_csv_data(csv_path):
    """Wczytuje dane kontrahentów z pliku CSV. Klucz = znormalizowany NIP."""
    csv_data = {}
    skipped_count = 0
    duplicate_count = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            raw_nip = row.get("NIP", "").strip()
            if not raw_nip:
                skipped_count += 1
                continue

            normalized = normalize_nip(raw_nip)
            if not normalized:
                skipped_count += 1
                continue

            if normalized in csv_data:
                duplicate_count += 1

            csv_data[normalized] = {
                "nazwa": row.get("Nazwa kontrahenta", "").strip(),
                "raw_nip": raw_nip,
                "Grupa firm": row.get("Grupa firm", "").strip(),
                "Branża": row.get("Branża", "").strip(),
                "Profil kontrahenta": row.get("Profil kontrahenta", "").strip(),
                "Typ kontrahenta": row.get("Typ kontrahenta", "").strip(),
            }

    console.print(f"Wczytano {len(csv_data)} kontrahentów z CSV.", style="bold blue")
    if skipped_count:
        console.print(f"Pominięto {skipped_count} rekordów bez NIP.", style="yellow")
    if duplicate_count:
        console.print(f"Nadpisano {duplicate_count} duplikatów NIP (zachowano ostatni wpis).", style="yellow")

    return csv_data


def find_fields_to_update(db_row, csv_record):
    """Porównuje dane z bazy z danymi z CSV i zwraca słownik pól do aktualizacji."""
    updates = {}
    details = []

    for csv_col, db_col in CSV_TO_DB_MAPPING.items():
        csv_value = csv_record.get(csv_col, "")
        if not csv_value:
            # CSV nie ma wartości dla tego pola — pomijamy
            continue

        # Pobierz aktualną wartość z bazy
        db_value = getattr(db_row, db_col, None) or ""

        if csv_value != db_value:
            updates[db_col] = csv_value
            details.append(f"{csv_col}: '{db_value}' -> '{csv_value}'")

    return updates, details


def update_record(cursor, wfd_signature, updates):
    """Aktualizuje rekord kontrahenta w tabeli WFElements po WFD_Signature."""
    set_clauses = []
    params = []
    for col, val in updates.items():
        set_clauses.append(f"{col} = ?")
        params.append(val)

    params.append(wfd_signature)
    query = f"UPDATE WFElements SET {', '.join(set_clauses)} WHERE WFD_Signature = ?"
    cursor.execute(query, tuple(params))


def process_kontrahenci(mode='test'):
    """Nawiązuje połączenie z bazą danych, porównuje dane z CSV i opcjonalnie aktualizuje kontrahentów."""
    connection = None
    updated_count = 0
    records_to_change = []

    try:
        # 1. Wczytanie danych z CSV
        if not os.path.exists(CSV_FILE_PATH):
            console.print(f"Nie znaleziono pliku CSV: {CSV_FILE_PATH}", style="bold red")
            return

        csv_data = load_csv_data(CSV_FILE_PATH)
        if not csv_data:
            console.print("Plik CSV jest pusty lub nie zawiera prawidłowych rekordów.", style="bold red")
            return

        # 2. Wczytanie zapytania SQL
        if not os.path.exists(SQL_FILE_PATH):
            console.print(f"Nie znaleziono pliku SQL: {SQL_FILE_PATH}", style="bold red")
            return

        sql_query = get_sql_from_file(SQL_FILE_PATH)

        # 3. Połączenie z bazą i pobranie kontrahentów
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

        # 4. Porównanie i przygotowanie listy aktualizacji
        matched_count = 0
        no_changes_count = 0

        with Progress() as progress:
            task = progress.add_task("Porównywanie danych...", total=len(db_rows))

            for db_row in db_rows:
                db_nip = normalize_nip(db_row.NIP)
                progress.advance(task)

                if not db_nip:
                    continue

                csv_record = csv_data.get(db_nip)
                if not csv_record:
                    continue

                matched_count += 1
                updates, details = find_fields_to_update(db_row, csv_record)

                if not updates:
                    no_changes_count += 1
                    continue

                records_to_change.append({
                    "wfd_signature": db_row.WFD_Signature,
                    "nazwa": db_row.NazwaKontrahenta or "",
                    "nip": db_row.NIP or "",
                    "updates": updates,
                    "details": details,
                })

        console.print(f"\nDopasowano {matched_count} kontrahentów po NIP.", style="bold blue")
        console.print(f"Bez zmian: {no_changes_count} rekordów.", style="dim")

        if not records_to_change:
            console.print("Nie znaleziono kontrahentów wymagających aktualizacji.", style="bold yellow")
            return

        console.print(f"Do aktualizacji: {len(records_to_change)} rekordów.\n", style="bold green")

        # 5. Aktualizacja i wyświetlenie raportu
        table = Table(title="Raport aktualizacji kontrahentów", show_header=True, header_style="bold magenta")
        table.add_column("Sygnatura", style="dim", width=15)
        table.add_column("Nazwa kontrahenta", width=40)
        table.add_column("NIP", width=18)
        table.add_column("Zmiany", width=60)
        table.add_column("Status", style="yellow", width=20)

        if mode in ('update', 'single'):
            total = 30 if mode == 'single' else len(records_to_change)
            with Progress() as update_progress:
                update_task = update_progress.add_task("Aktualizacja rekordów...", total=total)
                for record in records_to_change:
                    try:
                        update_record(cursor, record["wfd_signature"], record["updates"])
                        update_status = "[bold green]Zaktualizowano[/bold green]"
                        updated_count += 1
                    except Exception as e:
                        update_status = f"[bold red]Błąd: {e}[/bold red]"

                    update_progress.advance(update_task)

                    table.add_row(
                        str(record["wfd_signature"]),
                        record["nazwa"],
                        record["nip"],
                        "\n".join(record["details"]),
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
                    "\n".join(record["details"]),
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
        description="Aktualizuje dane kontrahentów w WEBCON BPS na podstawie pliku CSV.\n\n"
                    "Klucz dopasowania: NIP (z normalizacją — prefiks 'PL' jest usuwany).\n"
                    "Aktualizowane pola: Grupa firm, Branża, Profil kontrahenta, Typ kontrahenta.\n\n"
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

    process_kontrahenci(mode=mode)
