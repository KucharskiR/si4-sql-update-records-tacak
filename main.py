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
# Zakładamy, że obieg "Projekty" ma ID 61
SQL_QUERY = "SELECT WFD_ID, WFD_Signature, WFD_AttText1, WFD_AttText3 FROM WFElements WHERE WFD_DTYPEID = 61;"

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

        # Wyświetlanie nagłówków
        print(f"\n{'ID':<5} | {'Sygnatura':<15} | {'Numer Projektu':<20} | {'Nazwa Projektu'}")
        print("-" * 80)

        # Wyświetlanie danych
        for row in rows:
            print(f"{row.WFD_ID:<5} | {row.WFD_Signature:<15} | {row.WFD_AttText1:<20} | {row.WFD_AttText3}")

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
