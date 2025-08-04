# Automatyzacja Aktualizacji Danych Projektowych w WEBCON BPS

Ten projekt zawiera dwa skrypty w języku Python, które służą do analizy i aktualizacji danych projektowych przechowywanych w bazie danych WEBCON BPS. Głównym celem jest automatyczne parsowanie i uzupełnianie pól `Numer tematu`, `Kod zadania` oraz `Klient (skrót)` na podstawie informacji zawartych w polach `Numer projektu` i `Nazwa projektu`.

## Skrypty

1.  **`main.py`**
    *   **Cel:** Analiza i wizualizacja danych (tylko do odczytu).
    *   **Funkcjonalność:** Łączy się z bazą danych, pobiera dane projektowe, przetwarza je w pamięci (bez zapisu do bazy) i wyświetla w czytelnej, kolorowej tabeli w terminalu. Idealny do weryfikacji, które projekty wymagają aktualizacji.

2.  **`main_updater.py`**
    *   **Cel:** Aktualizacja danych w bazie.
    *   **Funkcjonalność:** Rozszerza możliwości `main.py` o funkcję zapisu przetworzonych danych z powrotem do bazy. Skrypt oferuje trzy tryby pracy dla zapewnienia bezpieczeństwa operacji.

---

## Wymagania

*   Python 3.6+
*   Zainstalowany sterownik **ODBC Driver for SQL Server**.

---

## Instalacja i Konfiguracja

**1. Pobranie zależności**

Przejdź do katalogu `skrypt-python-aktualizacja-bazy` i zainstaluj wymagane biblioteki:
```bash
pip install -r requirements.txt
```

**2. Konfiguracja połączenia z bazą danych (`.env`)**

Jest to najważniejszy krok. Musisz utworzyć plik o nazwie `.env` w głównym katalogu skryptu (`skrypt-python-aktualizacja-bazy/.env`). Plik ten przechowuje poufne dane dostępowe do bazy i jest ignorowany przez Git.

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

**2. Aktualizacja danych**

Skrypt `main_updater.py` służy do zapisu zmian w bazie. Uruchamiaj go z odpowiednimi flagami:

*   **Tryb testowy (domyślny, "na sucho")**
    Wyświetla, co zostałoby zaktualizowane, ale nie dokonuje żadnych zmian w bazie.
    ```bash
    python main_updater.py
    ```

*   **Aktualizacja jednego rekordu (do testów zapisu)**
    Aktualizuje tylko pierwszy napotkany rekord, który wymaga zmian, a następnie kończy pracę. Idealne do sprawdzenia, czy zapis działa poprawnie.
    ```bash
    python main_updater.py --single
    ```

*   **Pełna aktualizacja wszystkich rekordów**
    Aktualizuje wszystkie rekordy, które tego wymagają. Ze względów bezpieczeństwa, przed uruchomieniem **poprosi o ostateczne potwierdzenie**.
    ```bash
    python main_updater.py --update-all
    ```
    Po uruchomieniu tego polecenia, wpisz `tak` i naciśnij Enter, aby rozpocząć masową aktualizację.

---

## Zależności

*   `pyodbc`: Do połączenia z bazą danych SQL Server.
*   `python-dotenv`: Do wczytywania zmiennych środowiskowych z pliku `.env`.
*   `rich`: Do wyświetlania danych w estetyczny, kolorowy sposób w terminalu.
