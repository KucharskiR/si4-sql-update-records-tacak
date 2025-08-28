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

def fetch_projects(only_missing=False):
    """Nawiązuje połączenie z bazą danych, pobiera, przetwarza i wyświetla projekty."""
    connection = None
    try:
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        console.print("Pobieranie i przetwarzanie projektów...", style="bold blue")
        cursor.execute(SQL_QUERY)
        rows = cursor.fetchall()

        if only_missing:
            rows = [row for row in rows if not row.Kod_zadania or not row.Numer_tematu or not row.Klient_skrot]
            console.print("Wyświetlanie tylko rekordów z brakującymi polami.", style="bold yellow")

        if not rows:
            console.print("Nie znaleziono żadnych projektów do wyświetlenia.", style="bold red")
            return

        columns = [column[0] for column in cursor.description]
        
        table = Table(title="Raport Projektów", show_header=True, header_style="bold magenta")
        for col in columns:
            table.add_column(col, style="dim", width=20)
        table.add_column("Informacje o Przetwarzaniu", style="green")

        for row in rows:
            processing_info = []
            
            # 1. Przetwarzanie 'Numer projektu'
            numer_projektu = row.Numer_projektu
            if numer_projektu and '_' in numer_projektu:
                parts = numer_projektu.split('_', 1)
                numer_tematu = parts[0]
                kod_zadania = parts[1]
                processing_info.append(f"Podzielono 'Numer projektu' -> Temat: {numer_tematu}, Zadanie: {kod_zadania}")

            # 2. Przetwarzanie 'Nazwa projektu'
            nazwa_projektu = row.Nazwa_projektu
            if nazwa_projektu and '_' in nazwa_projektu:
                klient_skrot = nazwa_projektu.split('_', 1)[0]
                processing_info.append(f"Wyodrębniono 'Klient (skrót)' -> {klient_skrot}")

            row_values = [str(item if item is not None else '') for item in row]
            row_values.append("\n".join(processing_info))
            table.add_row(*row_values)

        console.print(table)

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        console.print(f"Błąd połączenia z bazą danych: {sqlstate}", style="bold red")
        console.print(ex)
    except Exception as e:
        console.print(f"Wystąpił nieoczekiwany błąd: {e}", style="bold red")
    finally:
        if connection:
            connection.close()
            console.print("\nPołączenie z bazą danych zostało zamknięte.", style="bold blue")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analiza i wizualizacja danych projektowych w WEBCON BPS.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--only-missing", action="store_true", help="Wyświetl tylko te rekordy, które mają nieuzupełnione pola i mogą zostać zaktualizowane.")
    
    args = parser.parse_args()
    
    fetch_projects(only_missing=args.only_missing)