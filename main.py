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

# Zapytanie SQL do pobrania wszystkich kolumn dla projektów
# Zakładamy, że obieg "Projekty" ma ID 61
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
    """Nawiązuje połączenie z bazą danych, pobiera i wyświetla projekty."""
    connection = None
    try:
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        print("Pobieranie projektów...")
        cursor.execute(SQL_QUERY)
        rows = cursor.fetchall()

        if not rows:
            print("Nie znaleziono żadnych projektów.")
            return

        # Pobieranie nazw kolumn z kursora
        columns = [column[0] for column in cursor.description]

        # Wyświetlanie nagłówków
        print(" | ".join(columns))
        print("-" * (len(" | ".join(columns)) + 20)) # Dynamiczna szerokość

        # Wyświetlanie danych
        for row in rows:
            print(" | ".join(str(item) for item in row))

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