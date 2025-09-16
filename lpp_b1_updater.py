import os
import pyodbc
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
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

# Zapytanie SQL do pobrania odpowiednich projektów
SQL_QUERY = """
SELECT
    DET_ID,
    DET_Att2 as 'Numer_projektu',
    DET_Att4 as 'Nazwa_projektu'
FROM
    dbo.WFELEMENTDETAILS
WHERE
    DET_WFCONID = 1491
    AND (dbo.ClearWFElem(DET_Att2) = '3747_21' OR dbo.ClearWFElem(DET_Att2) = '3747_22')
    AND DET_Att4 LIKE '%hala B'
"""

def get_connection_string():
    """Tworzy connection string w zależności od metody uwierzytelniania."""
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};"
    else:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"

# Uproszczona funkcja aktualizacji - bez logiki historii
def update_record(cursor, det_id, new_nazwa_projektu):
    """Aktualizuje nazwę projektu w tabeli WFELEMENTDETAILS."""
    cursor.execute(
        "UPDATE WFELEMENTDETAILS SET DET_Att4 = ? WHERE DET_ID = ?",
        new_nazwa_projektu,
        det_id
    )

def process_projects(mode='test'):
    """Nawiązuje połączenie z bazą danych, pobiera, przetwarza i opcjonalnie aktualizuje projekty."""
    connection = None
    updated_count = 0
    records_to_change = []

    try:
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        console.print("Pobieranie i przetwarzanie projektów...", style="bold blue")
        cursor.execute(SQL_QUERY)
        rows = cursor.fetchall()

        if not rows:
            console.print("Nie znaleziono żadnych projektów do przetworzenia.", style="bold red")
            return

        for row in rows:
            nazwa_projektu_raw = row.Nazwa_projektu
            if not nazwa_projektu_raw:
                continue

            # Rozdzielenie ciągu znaków, aby uzyskać samą nazwę do sprawdzenia
            display_name = nazwa_projektu_raw
            if '#' in nazwa_projektu_raw:
                display_name = nazwa_projektu_raw.split('#', 1)[1]

            # Sprawdzenie, czy właściwa nazwa (po znaku #) kończy się na " hala B"
            if display_name.strip().endswith('_hala B'):
                # Modyfikacja polega na dodaniu "1" na końcu całego oryginalnego ciągu
                new_nazwa_projektu = nazwa_projektu_raw + "1"

                records_to_change.append({
                    "det_id": row.DET_ID,
                    "numer_projektu": row.Numer_projektu,
                    "old_nazwa": nazwa_projektu_raw,
                    "new_nazwa": new_nazwa_projektu
                })

        if not records_to_change:
            console.print("Nie znaleziono projektów pasujących do kryteriów.", style="bold yellow")
            return

        table = Table(title="Raport aktualizacji LPP 'hala B'", show_header=True, header_style="bold magenta")
        table.add_column("DET_ID", style="dim")
        table.add_column("Numer Projektu", width=30)
        table.add_column("Stara Nazwa Projektu", width=50)
        table.add_column("Nowa Nazwa Projektu", width=50)
        table.add_column("Status", style="yellow")

        for record in records_to_change:
            update_status = "Oczekuje (tryb testowy)"
            if mode == 'update':
                try:
                    update_record(cursor, record["det_id"], record["new_nazwa"])
                    update_status = "[bold green]Zaktualizowano[/bold green]"
                    updated_count += 1
                except Exception as e:
                    update_status = f"[bold red]Błąd: {e}[/bold red]"

            table.add_row(
                str(record["det_id"]),
                record["numer_projektu"],
                record["old_nazwa"],
                record["new_nazwa"],
                update_status
            )

        console.print(table)

        if mode == 'update':
            connection.commit()
            console.print(f"Zakończono. Zaktualizowano {updated_count} rekordów.", style="bold green")
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
        description="Aktualizuje nazwy projektów LPP 'hala B' w WEBCON BPS.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Uruchamia skrypt w trybie aktualizacji. Domyślnie działa w trybie testowym."
    )

    args = parser.parse_args()

    mode = 'test'
    if args.update:
        mode = 'update'
        console.print("UWAGA: Ta operacja zaktualizuje rekordy w bazie danych.", style="bold yellow")
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != 'tak':
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()

    process_projects(mode=mode)
