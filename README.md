# Automatyzacja Aktualizacji Danych w WEBCON BPS

Ten projekt zawiera skrypty w języku Python, które służą do analizy i aktualizacji danych przechowywanych w bazie danych WEBCON BPS.

## Skrypty

1.  **`main.py`**
    *   **Cel:** Analiza i wizualizacja danych projektowych (tylko do odczytu).
    *   **Funkcjonalność:** Parsuje pola `Numer projektu` i `Nazwa projektu`, aby uzupełnić `Numer tematu`, `Kod zadania` oraz `Klient (skrót)`. Działa w trybie tylko do odczytu, pokazując potencjalne zmiany.

2.  **`main_updater.py`**
    *   **Cel:** Aktualizacja danych projektowych w bazie.
    *   **Funkcjonalność:** Rozszerza możliwości `main.py` o funkcję zapisu przetworzonych danych projektu z powrotem do bazy.

3.  **`rcp_updater.py`**
    *   **Cel:** Aktualizacja wpisów Rejestracji Czasu Pracy (RCP).
    *   **Funkcjonalność:** Dla wpisów RCP w podanym zakresie dat, skrypt uzupełnia brakujące pola: `Jednostka organizacyjna`, `Kod jednostki organizacyjnej` oraz `Łączny czas`. Korzysta ze złożonej logiki SQL do odnalezienia prawidłowych danych na podstawie informacji o pracowniku i dacie wpisu.

4.  **`unified_unit_updater.py`**
    *   **Cel:** Ujednolicona aktualizacja ról (Prowadzący, Przypisani) i Jednostek Organizacyjnych dokumentów w bazie.
    *   **Funkcjonalność:** Opiera się o zdefiniowane w SQL (`sql/SQL_Unified_Unit.sql`) mapowania, aktualizując w locie wartości ról, na podstawie przypisań wyższej instancji. Zbudowany z wieloma mechanizmami zabezpieczającymi (wielostopniowe `dry-run`, limitowania i celowanie na sygnatury).

---

## Wymagania

*   Python 3.6+
*   Zainstalowany sterownik **ODBC Driver for SQL Server**.

---

## Instalacja i Konfiguracja

**1. Pobranie zależności**

Przejdź do głównego katalogu projektu i zainstaluj wymagane biblioteki:
```bash
pip install -r requirements.txt
```

**2. Konfiguracja połączenia z bazą danych (`.env`)**

Jest to najważniejszy krok. Musisz utworzyć plik o nazwie `.env` w głównym katalogu skryptu. Plik ten przechowuje poufne dane dostępowe do bazy i jest ignorowany przez Git.

Skrypt obsługuje dwie metody uwierzytelniania:

**Opcja A: Uwierzytelnianie Windows (zalecane)**

Jeśli masz dostęp do bazy danych przez swoje konto Windows, pozostaw puste pola `DB_USER` i `DB_PASSWORD`. Skrypt automatycznie użyje `Trusted_Connection`.

*Zawartość pliku `.env` dla uwierzytelniania Windows:*
```dotenv
DB_SERVER=NAZWA_TWOJEGO_SERWERA
DB_NAME=NAZWA_TWOJEJ_BAZY
DB_USER=
DB_PASSWORD=
```

**Opcja B: Uwierzytelnianie SQL Server**

Jeśli używasz dedykowanego użytkownika SQL, podaj jego login i hasło.

*Zawartość pliku `.env` dla uwierzytelniania SQL Server:*
```dotenv
DB_SERVER=NAZWA_TWOJEGO_SERWERA
DB_NAME=NAZWA_TWOJEJ_BAZY
DB_USER=twoj_login_sql
DB_PASSWORD=twoje_haslo_sql
```

> **Ważne:** Zastąp `NAZWA_TWOJEGO_SERWERA` i `NAZWA_TWOJEJ_BAZY` prawidłowymi wartościami dla Twojego środowiska.

---

## Użycie

**1. Analiza danych projektu (bez zapisu)**

Aby zobaczyć, które rekordy projektów zostaną przetworzone, uruchom skrypt `main.py`:
```bash
python main.py
```

**2. Aktualizacja danych projektu**

Skrypt `main_updater.py` służy do zapisu zmian w danych projektowych.

*   **Tryb testowy (domyślny, "na sucho")**
    Wyświetla, co zostałoby zaktualizowane, ale nie dokonuje żadnych zmian w bazie.
    ```bash
    python main_updater.py
    ```

*   **Pełna aktualizacja wszystkich rekordów projektu**
    Aktualizuje wszystkie rekordy projektów, które tego wymagają. Przed uruchomieniem **poprosi o ostateczne potwierdzenie**.
    ```bash
    python main_updater.py --update-all
    ```

**3. Aktualizacja wpisów RCP (`rcp_updater.py`)**

Ten skrypt wymaga podania zakresu dat, dla którego mają zostać zaktualizowane wpisy RCP.

*   **Tryb testowy (domyślny, "na sucho")**
    Wyświetla w tabeli, które wpisy RCP i jakie dane w nich zostaną zaktualizowane. Nie dokonuje żadnych zmian w bazie.
    ```bash
    python rcp_updater.py --start-date DD.MM.RRRR --end-date DD.MM.RRRR
    ```
    *Przykład:*
    ```bash
    python rcp_updater.py --start-date 01.11.2024 --end-date 30.11.2024
    ```

*   **Pełna aktualizacja wpisów RCP**
    Aktualizuje wszystkie wpisy RCP w podanym zakresie dat. Ze względów bezpieczeństwa, przed uruchomieniem **poprosi o ostateczne potwierdzenie (y/n)**.
    ```bash
    python rcp_updater.py --start-date DD.MM.RRRR --end-date DD.MM.RRRR --update
    ```
    *Przykład:*
    ```bash
    python rcp_updater.py --start-date 01.11.2024 --end-date 30.11.2024 --update
    ```

**4. Aktualizacja jednostek i ról (`unified_unit_updater.py`)**

Skrypt modyfikuje powiązania w dokumentach, aktualizując: `JO zgłaszającego`, `JO prowadząca`, `Przypisani` oraz `Prowadzący`. Oparty o ujednolicone zapytanie SQL.

*   **Tryb testowy (domyślny, "na sucho")**
    Wypisze w kolorowej tabeli wszystkie docelowe zmiany, podświetlając modyfikacje na czerwono-zielono. Nie zapisze żadnych zmian w bazie.
    ```bash
    python unified_unit_updater.py
    ```

*   **Tryb testowy dla pojedynczej sygnatury**
    Ogranicza podgląd zmian (nie modyfikując bazy) tylko dla jednego, wybranego wpisu o wskazanej Sygnaturze.
    ```bash
    python unified_unit_updater.py --signature "TWOJA_SYGNATURA"
    ```

*   **Aktualizacja wybranej liczby rekordów**
    Przetworzy i nadpisze w bazie tylko N pierwszych znalezionych wierszy do aktualizacji. Przed uruchomieniem zapytania o ostateczne potwierdzenie. Parametr `--single` domyślnie zatrzymuje się na 30 elementach. Parametrem `--limit` możemy ustawić własną ilość.
    ```bash
    python unified_unit_updater.py --single
    python unified_unit_updater.py --limit 10
    ```

*   **Aktualizacja wybranego, pojedynczego rekordu**
    Ograniczy analizę bazy i wyśle aktualizację `UPDATE` do bazy SQL wyłącznie dla jednego wybranego wpisu.
    ```bash
    python unified_unit_updater.py --update-signature "TWOJA_SYGNATURA"
    ```

*   **Pełna aktualizacja**
    Skrypt przeliczy i uaktualni wszystkie pasujące rekordy w całej bazie na produkcji. Przed uruchomieniem wymaga ostatecznego potwierdzenia.
    ```bash
    python unified_unit_updater.py --update
    ```

---

## Debugowanie z `ipdb`

Do debugowania skryptów można wykorzystać bibliotekę `ipdb`, która pozwala na interaktywne zatrzymanie programu i analizę jego stanu.

**1. Instalacja**

Upewnij się, że `ipdb` jest zainstalowane, uruchamiając:
```bash
pip install -r requirements.txt
```

**2. Użycie**

Aby rozpocząć sesję debugowania, wykonaj dwa proste kroki:

*   **Zaimportuj bibliotekę** na początku pliku, który chcesz debugować:
    ```python
    import ipdb
    ```

*   **Ustaw punkt przerwania (breakpoint)** w miejscu, w którym chcesz zatrzymać wykonanie skryptu, wstawiając poniższą linię:
    ```python
    ipdb.set_trace()
    ```

Po uruchomieniu skryptu jego wykonanie zatrzyma się w miejscu, gdzie wstawiłeś `set_trace()`, a Ty uzyskasz dostęp do interaktywnej konsoli debuggera.

---

## Zależności

*   `pyodbc`: Do połączenia z bazą danych SQL Server.
*   `python-dotenv`: Do wczytywania zmiennych środowiskowych z pliku `.env`.
*   `rich`: Do wyświetlania danych w estetyczny, kolorowy sposób w terminalu.
*   `ipdb`: Do interaktywnego debugowania skryptów.