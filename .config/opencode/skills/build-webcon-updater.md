---
name: build-webcon-updater
description: Tworzenie bezpiecznych skryptów Python do modyfikacji danych w bazie WEBCON BPS.
---

# SKILL: Budowa aktualizatorów bazy danych WEBCON BPS (Python)

Ten skill zawiera wytyczne dotyczące budowania oraz modyfikacji skryptów (updaterów) w języku Python do ingerencji w bazę danych WEBCON BPS (MS SQL Server).

## 1. Główne założenia (ZŁOTE ZASADY)

*   **DRY-RUN DEFAULT (Safe-by-default)**: Każdy skrypt **musi** domyślnie działać w trybie testowym (tylko odczyt, "na sucho"). Użytkownik musi ręcznie podać parametr (np. `--update`, `--single`), aby zapisywać zmiany.
*   **PARAMETRYZACJA**: Używaj parametryzacji `pyodbc` (symbol zapytania `?`) zamiast zwykłego sklejania tekstu w zapytaniach SQL, aby uniknąć ataków SQL Injection.
*   **TRANSAKCYJNOŚĆ**: Otwieraj połączenia na początku bazy, zatwierdzaj zapisy poleceniem `commit()` po pełnej pętli modyfikacyjnej i wykonuj `rollback()` we fragmencie `except` wyłapującym błędy `pyodbc.Error`.
*   **INTERFEJS UŻYTKOWNIKA**: Wyprowadzaj dane do terminala jako schludne tabele w bibliotece `rich`. Raportowanie zmian (przed i po) dla każdego rekordu jest wymagane.

## 2. Architektura danych WEBCON BPS

*   `WFElements`: Główna tabela zawierająca element obiegu (dokument/sprawę).
*   `WFElementDetails`: Tabela dla list pozycji przypisanych do elementów (wielowierszowych).
*   `WFD_Signature`: Najważniejszy identyfikator do aktualizowania i wyświetlania pojedynczego rekordu dokumentu.
*   **Typy pól**:
    *   *Tekstowe*: Zazwyczaj `WFD_AttTextX` (np. WFD_AttText6)
    *   *Słownikowe (Choice)*: Zazwyczaj `WFD_AttChooseX`. Zawierają ID i nazwę rekordu sformatowaną jako `ID#Nazwa` (np. `123#Opcja A`). Jeżeli przypisujemy rolę lub pole wyboru w skrypcie, musimy zachować format `ID#Nazwa` albo skorzystać z identyfikatora.
    *   *Daty*: Zazwyczaj `WFD_AttDateTimeX` (w formacie standardowym MSSQL np. pobieranym przez pyodbc jako `datetime.datetime`). Pola `Data od`/`Data do` potrafią być traktowane jako testowe po mapowaniu (np. formaty `DD.MM.YYYY` w `WFElementDetails`).
    
## 3. Szkielet kodu ("Boilerplate")

*Użyj poniższego szkieletu tworząc nowy skrypt:*

```python
import os
import pyodbc
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import argparse

# Inicjalizacja konfiguracji
load_dotenv()
console = Console()

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection_string():
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;"
    else:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;TrustServerCertificate=yes;"

def process_data(mode="test"):
    connection = pyodbc.connect(get_connection_string())
    cursor = connection.cursor()

    try:
        # Pobranie danych
        cursor.execute("SELECT WFD_Signature, WFD_AttText1 FROM WFElements WHERE ...")
        rows = cursor.fetchall()
        
        # Logika sprawdzająca
        # ...
        
        # Aktualizacja
        if mode == "update":
            for record in records_to_update:
                cursor.execute("UPDATE WFElements SET WFD_AttText1 = ? WHERE WFD_Signature = ?", (nowa_wartosc, sygnatura))
            connection.commit()
            console.print("[green]Zaktualizowano rekordy![/green]")

    except pyodbc.Error as ex:
        connection.rollback()
        console.print(f"[red]Błąd SQL: {ex}[/red]")
    finally:
        connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mój Updater.")
    parser.add_argument("--update", action="store_true", help="Tryb zapisu")
    args = parser.parse_args()
    
    mode = "update" if args.update else "test"
    if mode == "update":
        if input("Potwierdzasz zmiany? (tak/nie): ") != "tak":
            exit()
            
    process_data(mode)
```

## 4. Kluczowe procedury

### 1. Radzenie sobie ze zwracaniem duplikatów z JOIN (Deduplikacja SQL)
Webcon posiada wiele powiązanych tabel (jak grupy docelowe z `WFElementDetails`). Jeśli zmieniamy parametr SQL-a z `=` na `IN()`, `fetchall()` może zwrócić nam wiele zduplikowanych rekordów z tą samą instancją (sygnaturą `WFD_Signature`). Należy połączyć pobrane wyniki z SQL najpierw w Pythonowe zgrupowane słowniki (np. poprzez `collections.defaultdict`) grupując logikę wokół nadrzędnej sygnatury. 

### 2. Porównywanie i parsowanie dat
Pamiętaj, że skrypty pobierające metadane i właściwości wpisane z poziomu ręcznego dodawania Webcon mogą zwracać teksty a nie daty bazodanowe (np. jako format ISO, albo w standardzie polskim `DD.MM.YYYY`). Przed jakimikolwiek warunkami `data1 > data2` należy dokonać normalizacji do obiektu Pythonowej `datetime.date`. Pamiętaj też by usunąć marginesy błędu wynikające z porównywania godzin. 

### 3. Argument filtrujący dla "single runs" (`--signature`)
Nowoczesne buildery powinny udostępniać użytkownikom parametr wiersza poleceń np. `--signature "XYZ"`. Taki parametr nadpisuje instancję SQL dynamicznie doklejając `WHERE WFD_Signature = ?` aby wyfiltrować konkretny, pojedynczy przypadek na testach na suchej bazie. Ułatwia to sprawdzanie warunków brzegowych bez zrzucania wszystkich tysięcy instancji w Webconie.
