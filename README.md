# Automatyzacja Aktualizacji Danych Projektowych w WEBCON BPS

Ten projekt zawiera dwa skrypty w języku Python, które służą do analizy i aktualizacji danych projektowych przechowywanych w bazie danych WEBCON BPS. Głównym celem jest automatyczne parsowanie i uzupełnianie pól `Numer tematu`, `Kod zadania` oraz `Klient (skrót)` na podstawie informacji zawartych w polach `Numer projektu` i `Nazwa projektu`.

## Skrypty

1.  **`main.py`**
    *   **Cel:** Analiza i wizualizacja danych (tylko do odczytu).
    *   **Funkcjonalność:** Łączy się z bazą danych, pobiera dane projektowe, przetwarza je w pamięci (bez zapisu do bazy) i wyświetla w czytelnej, kolorowej tabeli w terminalu. Idealny do weryfikacji, które projekty wymagają aktualizacji. Posiada opcję filtrowania, aby pokazać tylko rekordy z brakującymi danymi.

2.  **`main_updater.py`**
    *   **Cel:** Aktualizacja danych w bazie.
    *   **Funkcjonalność:** Rozszerza możliwości `main.py` o funkcję zapisu przetworzonych danych z powrotem do bazy. Skrypt oferuje trzy tryby pracy oraz opcję filtrowania, aby operacje dotyczyły tylko rekordów z brakującymi danymi.

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

**1. Analiza danych (bez zapisu)**

Aby zobaczyć, które rekordy zostaną przetworzone, uruchom skrypt `main.py`:
```bash
python main.py
```

*   **Analiza tylko rekordów z brakami**
    Aby wyświetlić tylko te rekordy, w których brakuje `Kodu zadania`, `Numeru tematu` lub `Klienta (skrót)`:
    ```bash
    python main.py --only-missing
    ```

**2. Aktualizacja danych**

Skrypt `main_updater.py` służy do zapisu zmian w bazie. Uruchamiaj go z odpowiednimi flagami:

*   **Tryb testowy (domyślny, "na sucho")**
    Wyświetla, co zostałoby zaktualizowane, ale nie dokonuje żadnych zmian w bazie. Działa na wszystkich rekordach.
    ```bash
    python main_updater.py
    ```

*   **Tryb testowy dla rekordów z brakami**
    Działa jak tryb testowy, ale pokazuje zmiany tylko dla rekordów z brakującymi polami.
    ```bash
    python main_updater.py --only-missing
    ```

*   **Aktualizacja jednego rekordu (do testów zapisu)**
    Aktualizuje tylko pierwszy napotkany rekord, który wymaga zmian, a następnie kończy pracę. Można połączyć z `--only-missing`, aby działać na pierwszym rekordzie z brakami.
    ```bash
    python main_updater.py --single
    python main_updater.py --only-missing --single
    ```

*   **Pełna aktualizacja wszystkich rekordów**
    Aktualizuje wszystkie rekordy, które tego wymagają. Ze względów bezpieczeństwa, przed uruchomieniem **poprosi o ostateczne potwierdzenie**. Można połączyć z `--only-missing`, aby zaktualizować wszystkie rekordy z brakami.
    ```bash
    python main_updater.py --update-all
    python main_updater.py --only-missing --update-all
    ```
    Po uruchomieniu tego polecenia, wpisz `tak` i naciśnij Enter, aby rozpocząć masową aktualizację.

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

*   **Zaimportuj bibliotekę** na początku pliku, który chcesz debugować (`main.py` lub `main_updater.py`):
    ```python
    import ipdb
    ```

*   **Ustaw punkt przerwania (breakpoint)** w miejscu, w którym chcesz zatrzymać wykonanie skryptu, wstawiając poniższą linię:
    ```python
    ipdb.set_trace()
    ```

Po uruchomieniu skryptu jego wykonanie zatrzyma się w miejscu, gdzie wstawiłeś `set_trace()`, a Ty uzyskasz dostęp do interaktywnej konsoli debuggera.

**Podstawowe komendy `ipdb`:**

*   `n` (next) – wykonaj następną linię kodu.
*   `c` (continue) – kontynuuj normalne wykonywanie skryptu aż do następnego punktu przerwania.
*   `q` (quit) – zakończ sesję debugowania i wyjdź ze skryptu.
*   `p <zmienna>` (print) – wyświetl wartość podanej zmiennej (np. `p row`).
*   `l` (list) – pokaż, w którym miejscu w kodzie aktualnie się znajdujesz.

---

## Zależności

*   `pyodbc`: Do połączenia z bazą danych SQL Server.
*   `python-dotenv`: Do wczytywania zmiennych środowiskowych z pliku `.env`.
*   `rich`: Do wyświetlania danych w estetyczny, kolorowy sposób w terminalu.
*   `ipdb`: Do interaktywnego debugowania skryptów.