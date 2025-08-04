import os
import pyodbc
from dotenv import load_dotenv

# Załadowanie zmiennych środowiskowych z pliku .env
load_dotenv()

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
        # Uwierzytelnianie SQL Server
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};"
    else:
        # Uwierzytelnianie Windows
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"

def fetch_projects():
    """Nawiązuje połączenie z bazą danych, pobiera, przetwarza i wyświetla projekty."""
    connection = None
    try:
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        print("Pobieranie i przetwarzanie projektów...")
        cursor.execute(SQL_QUERY)
        rows = cursor.fetchall()

        if not rows:
            print("Nie znaleziono żadnych projektów.")
            return

        # Pobieranie nazw kolumn z kursora
        columns = [column[0] for column in cursor.description]

        # Wyświetlanie nagłówków
        header = " | ".join(f"{col:<20}" for col in columns)
        print(header)
        print("-" * len(header))

        # Przetwarzanie i wyświetlanie danych
        for row in rows:
            # Wyświetlanie oryginalnych danych
            row_values = [str(item if item is not None else '') for item in row]
            print(" | ".join(f"{val:<20}" for val in row_values))

            # 1. Przetwarzanie 'Numer projektu'
            numer_projektu = row.Numer_projektu
            if numer_projektu and '_' in numer_projektu:
                parts = numer_projektu.split('_', 1)
                numer_tematu = parts[0]
                kod_zadania = parts[1]
                print(f"  -> INFO: Podzielono 'Numer projektu' -> Nowy 'Numer tematu': {numer_tematu}, Nowy 'Kod zadania': {kod_zadania}")

            # 2. Przetwarzanie 'Nazwa projektu'
            nazwa_projektu = row.Nazwa_projektu
            if nazwa_projektu and '_' in nazwa_projektu:
                klient_skrot = nazwa_projektu.split('_', 1)[0]
                print(f"  -> INFO: Wyodrębniono 'Klient (skrót)' z 'Nazwa projektu' -> Nowy 'Klient (skrót)': {klient_skrot}")
            
            print("-" * len(header))

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Błąd połączenia z bazą danych: {sqlstate}")
        print(ex)
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {e}")
    finally:
        if connection:
            connection.close()
            print("\nPołączenie z bazą danych zostało zamknięte.")

if __name__ == "__main__":
    fetch_projects()
