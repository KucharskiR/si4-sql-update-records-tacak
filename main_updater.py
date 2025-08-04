import os
import pyodbc
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import argparse

# Załadowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Inicjalizacja konsoli Rich
console = Console()

# Pobranie danych konfiguracyjnych
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Zapytanie SQL do pobrania projektów
SQL_QUERY = """
SELECT
    WFD_ID,
    WFD_AttText1 AS 'Numer_projektu',
    WFD_AttText10 AS 'Kod_zadania',
    WFD_AttText9 AS 'Numer_tematu',
    WFD_AttText3 AS 'Nazwa_projektu',
    dbo.ClearWFElem(WFD_AttChoose11) AS 'Status',
    WFD_AttText8 AS 'Klient_skrot'
FROM
    WFElements
WHERE
    WFD_DTYPEID = 61;
"""

def get_connection_string():
    """Tworzy connection string w zależności od metody uwierzytelniania."""
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};"
    else:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"

def update_database_record(cursor, wfd_id, new_data):
    """Aktualizuje pojedynczy rekord w bazie danych."""
    update_query = "UPDATE WFElements SET "
    params = []
    for key, value in new_data.items():
        update_query += f"{key} = ?, "
        params.append(value)
    
    update_query = update_query.rstrip(", ") + " WHERE WFD_ID = ?"
    params.append(wfd_id)
    
    cursor.execute(update_query, tuple(params))

def process_and_update_projects(mode='test'):
    """Nawiązuje połączenie z bazą danych, pobiera, przetwarza i opcjonalnie aktualizuje projekty."""
    connection = None
    updated_count = 0
    try:
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        console.print("Pobieranie i przetwarzanie projektów...", style="bold blue")
        cursor.execute(SQL_QUERY)
        rows = cursor.fetchall()

        if not rows:
            console.print("Nie znaleziono żadnych projektów.", style="bold red")
            return

        columns = [column[0] for column in cursor.description]
        
        table = Table(title="Raport Projektów", show_header=True, header_style="bold magenta")
        for col in columns:
            table.add_column(col, style="dim", width=20)
        table.add_column("Informacje o Przetwarzaniu", style="green")
        table.add_column("Status Aktualizacji", style="yellow")

        for row in rows:
            new_data = {}
            processing_info = []
            update_status = "Pominięto (tryb testowy)"

            # 1. Przetwarzanie 'Numer projektu'
            numer_projektu = row.Numer_projektu
            if numer_projektu and '_' in numer_projektu:
                parts = numer_projektu.split('_', 1)
                new_data['WFD_AttText9'] = parts[0]  # Numer tematu
                new_data['WFD_AttText10'] = parts[1] # Kod zadania
                processing_info.append(f"Podzielono 'Numer projektu' -> Temat: {parts[0]}, Zadanie: {parts[1]}")

            # 2. Przetwarzanie 'Nazwa projektu'
            nazwa_projektu = row.Nazwa_projektu
            if nazwa_projektu and '_' in nazwa_projektu:
                new_data['WFD_AttText8'] = nazwa_projektu.split('_', 1)[0] # Klient (skrót)
                processing_info.append(f"Wyodrębniono 'Klient (skrót)' -> {new_data['WFD_AttText8']}")

            if new_data and mode != 'test':
                update_database_record(cursor, row.WFD_ID, new_data)
                update_status = f"[bold green]Zaktualizowano[/bold green] (ID: {row.WFD_ID})"
                updated_count += 1
                if mode == 'single':
                    connection.commit()
                    # Add the current row to the table before printing and exiting
                    row_values = [str(item if item is not None else '') for item in row]
                    row_values.append("\n".join(processing_info))
                    row_values.append(update_status)
                    table.add_row(*row_values)
                    console.print(table)
                    console.print(f"Zaktualizowano pojedynczy rekord (WFD_ID: {row.WFD_ID}) i zakończono.", style="bold green")
                    return
            elif not new_data:
                 update_status = "Brak zmian"
            
            row_values = [str(item if item is not None else '') for item in row]
            row_values.append("\n".join(processing_info))
            row_values.append(update_status)
            table.add_row(*row_values)

        console.print(table)
        
        if mode == 'all':
            connection.commit()
            console.print(f"Zakończono. Zaktualizowano {updated_count} rekordów.", style="bold green")
        elif mode == 'single':
             console.print("Nie znaleziono rekordu do aktualizacji w trybie pojedynczym.", style="bold yellow")


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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Przetwarzanie i aktualizacja projektów w WEBCON BPS.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--single", action="store_true", help="Aktualizuj tylko PIERWSZY pasujący rekord i zakończ (do testów zapisu).")
    mode_group.add_argument("--update-all", action="store_true", help="Aktualizuj WSZYSTKIE pasujące rekordy w bazie danych.")

    args = parser.parse_args()

    mode = 'test'
    if args.single:
        mode = 'single'
    elif args.update_all:
        mode = 'all'

    if mode == 'all':
        console.print("UWAGA: Ta operacja zaktualizuje wszystkie pasujące rekordy w bazie danych.", style="bold yellow")
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != 'tak':
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()
            
    process_and_update_projects(mode=mode)

