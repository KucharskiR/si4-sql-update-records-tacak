import os
import pyodbc
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import argparse
from datetime import datetime

# Załadowanie zmiennych środowiskowych
load_dotenv()

# Inicjalizacja konsoli
console = Console()

# Konfiguracja bazy danych
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Ścieżka do pliku SQL z zapytaniem pobierającym dane
SQL_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sql", "SQL_Unified_Unit.sql"
)

# Mapowanie kolumn, które chcemy zaktualizować (do dostosowania nazwy w bazie jeśli są inne)
# WFD_AttText6 = JO zgłaszającego
# WFD_AttChoose12 = JO prowadząca
# WFD_AttChoose4 = Przypisani
# WFD_AttChoose3 = Prowadzący
# Źródło danych z zapytania:
# 'Nazwa jednostki' -> D78_T.WFD_AttText1
# 'Zgłaszający SmartPTR' -> D63.WFD_AttChoose10


def get_connection_string():
    """Tworzy connection string w zależności od metody uwierzytelniania."""
    if DB_USER and DB_PASSWORD:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;"
    else:
        return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;TrustServerCertificate=yes;"


def get_sql_from_file(file_path):
    """Wczytuje zapytanie SQL z pliku."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_date(date_val):
    """Próbuje bezpiecznie przekształcić string/datetime do obiektu daty w celach porównawczych."""
    if not date_val:
        return None

    if isinstance(date_val, datetime):
        return date_val.date()

    if isinstance(date_val, str):
        date_str = date_val.strip()[:10]
        if not date_str:
            return None
        try:
            # Format standardowy ISO: YYYY-MM-DD
            if "-" in date_str:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            # Format polski: DD.MM.YYYY
            elif "." in date_str:
                return datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            pass

    return None


def update_record(cursor, wfd_signature, updates):
    """Aktualizuje rekord w tabeli WFElements po WFD_Signature."""
    set_clauses = []
    params = []
    for col, val in updates.items():
        set_clauses.append(f"{col} = ?")
        params.append(val)

    params.append(wfd_signature)
    query = f"UPDATE WFElements SET {', '.join(set_clauses)} WHERE WFD_Signature = ?"
    cursor.execute(query, tuple(params))


def process_unified_unit(mode="test", target_signature=None, limit_count=30):
    """Nawiązuje połączenie z bazą danych, pobiera dane z zapytania i opcjonalnie aktualizuje rekordy."""
    connection = None
    updated_count = 0
    records_to_change = []

    try:
        # 1. Wczytanie zapytania SQL
        if not os.path.exists(SQL_FILE_PATH):
            console.print(
                f"Nie znaleziono pliku SQL: {SQL_FILE_PATH}", style="bold red"
            )
            return

        sql_query = get_sql_from_file(SQL_FILE_PATH)

        # 2. Połączenie z bazą i pobranie danych
        conn_str = get_connection_string()
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()

        console.print("Pobieranie danych z bazy...", style="bold blue")
        if target_signature:
            # Używamy REPLACE, żeby usunąć z końcówki ';' jeżeli jest, żeby bezpiecznie dokleić AND
            safe_query = sql_query.rstrip().rstrip(";") + " AND D63.WFD_Signature = ?;"
            cursor.execute(safe_query, (target_signature,))
        else:
            cursor.execute(sql_query)

        db_rows = cursor.fetchall()

        if not db_rows:
            console.print(
                "Nie znaleziono żadnych rekordów w bazie danych.", style="bold red"
            )
            return

        console.print(
            f"Pobrano {len(db_rows)} rekordów z bazy danych.", style="bold blue"
        )

        # 3. Analiza danych i przygotowanie listy aktualizacji
        from collections import defaultdict

        grouped_rows = defaultdict(list)
        for row in db_rows:
            grouped_rows[row.WFD_Signature].append(row)

        matched_count = len(grouped_rows)
        no_changes_count = 0

        with Progress() as progress:
            task = progress.add_task("Analiza danych...", total=len(grouped_rows))

            for signature, rows in grouped_rows.items():
                progress.advance(task)

                base_row = rows[0]
                zglaszajacy_smartptr = (
                    getattr(base_row, "Zgłaszający SmartPTR", "") or ""
                )

                aktualne_jo_zglaszajacego = (
                    getattr(base_row, "JO zgłaszjącego (SmartPTR)", "") or ""
                )
                aktualna_jo_prowadzaca = getattr(base_row, "JO prowadząca", "") or ""
                aktualny_prowadzacy = getattr(base_row, "Prowadzący", "") or ""
                aktualni_przypisani = getattr(base_row, "Przypisani", "") or ""

                # Szukamy prawidłowej "Nazwa jednostki" analizując przedziały czasowe we wszystkich wierszach
                valid_nazwa_jednostki = ""
                for row in rows:
                    data_od = parse_date(getattr(row, "Data od", None))
                    data_do = parse_date(getattr(row, "Data do", None))
                    data_utworzenia = parse_date(
                        getattr(row, "Data utworzenia projektu", None)
                    )

                    is_valid = True
                    if data_utworzenia:
                        if data_od and data_utworzenia < data_od:
                            is_valid = False
                        if data_do and data_utworzenia > data_do:
                            is_valid = False

                    if is_valid:
                        nazwa = getattr(row, "Nazwa jednostki", "") or ""
                        id_jednostki = getattr(row, "ID_Jednostki_Organizacyjnej", "")
                        if nazwa:
                            if id_jednostki is not None and str(id_jednostki).strip():
                                valid_nazwa_jednostki = f"{id_jednostki}#{nazwa}"
                            else:
                                valid_nazwa_jednostki = nazwa
                            break

                updates = {}

                # Zakładamy nowe wartości na podstawie wymagań
                nowe_jo_zglaszajacego = valid_nazwa_jednostki

                # Jeśli nie ma "Nazwa jednostki" z poprawnego przedziału dat, nie nadpisuj JO
                if not valid_nazwa_jednostki and aktualne_jo_zglaszajacego:
                    nowe_jo_zglaszajacego = aktualne_jo_zglaszajacego

                nowe_jo_prowadzaca = (
                    nowe_jo_zglaszajacego  # JO prowadząca na podstawie JO zgłaszającego
                )
                nowy_przypisani = zglaszajacy_smartptr
                nowy_prowadzacy = zglaszajacy_smartptr

                columns_info = {
                    "jo_zglaszajacego": "",
                    "jo_prowadzaca": "",
                    "przypisani": "",
                    "prowadzacy": "",
                }

                # Sprawdzamy co trzeba zaktualizować
                # JO zgłaszającego
                if aktualne_jo_zglaszajacego != nowe_jo_zglaszajacego:
                    updates["WFD_AttText6"] = nowe_jo_zglaszajacego
                    columns_info["jo_zglaszajacego"] = (
                        f"[red]{aktualne_jo_zglaszajacego}[/red]\n-> [green]{nowe_jo_zglaszajacego}[/green]"
                    )
                else:
                    columns_info["jo_zglaszajacego"] = (
                        f"[dim]{aktualne_jo_zglaszajacego}[/dim]"
                    )

                # JO prowadząca
                if aktualna_jo_prowadzaca != nowe_jo_prowadzaca:
                    updates["WFD_AttChoose12"] = nowe_jo_prowadzaca
                    columns_info["jo_prowadzaca"] = (
                        f"[red]{aktualna_jo_prowadzaca}[/red]\n-> [green]{nowe_jo_prowadzaca}[/green]"
                    )
                else:
                    columns_info["jo_prowadzaca"] = (
                        f"[dim]{aktualna_jo_prowadzaca}[/dim]"
                    )

                # Przypisani
                if aktualni_przypisani != nowy_przypisani:
                    updates["WFD_AttChoose4"] = nowy_przypisani
                    columns_info["przypisani"] = (
                        f"[red]{aktualni_przypisani}[/red]\n-> [green]{nowy_przypisani}[/green]"
                    )
                else:
                    columns_info["przypisani"] = f"[dim]{aktualni_przypisani}[/dim]"

                # Prowadzący
                if aktualny_prowadzacy != nowy_prowadzacy:
                    updates["WFD_AttChoose3"] = nowy_prowadzacy
                    columns_info["prowadzacy"] = (
                        f"[red]{aktualny_prowadzacy}[/red]\n-> [green]{nowy_prowadzacy}[/green]"
                    )
                else:
                    columns_info["prowadzacy"] = f"[dim]{aktualny_prowadzacy}[/dim]"

                if not updates:
                    no_changes_count += 1
                    continue

                records_to_change.append(
                    {
                        "wfd_signature": signature,
                        "updates": updates,
                        "columns_info": columns_info,
                    }
                )

        console.print(
            f"\nPrzeanalizowano {matched_count} unikalnych rekordów.", style="bold blue"
        )
        console.print(f"Bez zmian: {no_changes_count} rekordów.", style="dim")

        if not records_to_change:
            console.print(
                "Nie znaleziono rekordów wymagających aktualizacji.",
                style="bold yellow",
            )
            return

        console.print(
            f"Do aktualizacji: {len(records_to_change)} rekordów.\n", style="bold green"
        )

        # 4. Aktualizacja i wyświetlenie raportu
        table = Table(
            title="Raport aktualizacji JO i ról",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Sygnatura", style="dim", width=12)
        table.add_column("JO zgłaszającego", width=25)
        table.add_column("JO prowadząca", width=25)
        table.add_column("Przypisani", width=25)
        table.add_column("Prowadzący", width=25)
        table.add_column("Status", style="yellow", width=15)

        if mode in ("update", "single", "limit", "update_signature"):
            if mode in ("single", "limit"):
                total = limit_count
            else:
                total = len(records_to_change)

            with Progress() as update_progress:
                update_task = update_progress.add_task(
                    "Aktualizacja rekordów...", total=total
                )
                for record in records_to_change:
                    try:
                        update_record(
                            cursor, record["wfd_signature"], record["updates"]
                        )
                        update_status = "[bold green]Zaktualizowano[/bold green]"
                        updated_count += 1
                    except Exception as e:
                        update_status = f"[bold red]Błąd: {e}[/bold red]"

                    update_progress.advance(update_task)

                    ci = record["columns_info"]
                    table.add_row(
                        str(record["wfd_signature"]),
                        ci["jo_zglaszajacego"],
                        ci["jo_prowadzaca"],
                        ci["przypisani"],
                        ci["prowadzacy"],
                        update_status,
                    )

                    if mode in ("single", "limit") and updated_count >= limit_count:
                        break
        else:
            for record in records_to_change:
                ci = record["columns_info"]
                table.add_row(
                    str(record["wfd_signature"]),
                    ci["jo_zglaszajacego"],
                    ci["jo_prowadzaca"],
                    ci["przypisani"],
                    ci["prowadzacy"],
                    "Oczekuje",
                )

        console.print(table)

        if mode in ("update", "update_signature"):
            connection.commit()
            console.print(
                f"Zakończono. Zaktualizowano {updated_count} rekordów.",
                style="bold green",
            )
        elif mode in ("single", "limit"):
            connection.commit()
            console.print(
                f"Zakończono w trybie z limitem. Zaktualizowano {updated_count} z maks. {limit_count} rekordów.",
                style="bold green",
            )
        else:
            console.print(
                f"Tryb testowy zakończony. {len(records_to_change)} rekordów zostałoby zaktualizowanych.",
                style="bold yellow",
            )

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
            console.print(
                "\nPołączenie z bazą danych zostało zamknięte.", style="bold blue"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aktualizuje dane jednostek i ról w WEBCON BPS na podstawie zapytania SQL.\n\n"
        "Aktualizowane pola:\n"
        "- JO zgłaszającego = ID_Jednostki#Nazwa jednostki\n"
        "- JO prowadząca = JO zgłaszającego\n"
        "- Przypisani = Zgłaszający (SmartPTR)\n"
        "- Prowadzący = Zgłaszający (SmartPTR)\n\n"
        "Domyślnie działa w trybie testowym (dry-run) — nie wprowadza zmian w bazie.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--single",
        action="store_true",
        help="Aktualizuj tylko pierwsze 30 rekordów (do testów zapisu).",
    )
    mode_group.add_argument(
        "--update",
        action="store_true",
        help="Aktualizuj WSZYSTKIE pasujące rekordy w bazie danych.",
    )
    mode_group.add_argument(
        "--limit",
        type=int,
        help="Aktualizuj tylko podaną liczbę rekordów.",
    )
    mode_group.add_argument(
        "--update-signature",
        type=str,
        help="Aktualizuj tylko jeden konkretny rekord o podanej Sygnaturze.",
    )

    # Argument filtrujący (działa niezależnie od trybu, np. dla testów jednego wpisu)
    parser.add_argument(
        "--signature",
        type=str,
        help="Ogranicz działanie skryptu (nawet w trybie testowym) do konkretnej Sygnatury.",
    )

    args = parser.parse_args()

    mode = "test"
    target_signature = args.signature
    limit_count = 30  # default for single

    if args.single:
        mode = "single"
        console.print(
            "UWAGA: Ta operacja zaktualizuje do 30 rekordów w bazie danych.",
            style="bold yellow",
        )
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != "tak":
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()
    elif args.limit:
        mode = "limit"
        limit_count = args.limit
        console.print(
            f"UWAGA: Ta operacja zaktualizuje do {limit_count} rekordów w bazie danych.",
            style="bold yellow",
        )
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != "tak":
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()
    elif args.update:
        mode = "update"
        console.print(
            "UWAGA: Ta operacja zaktualizuje WSZYSTKIE pasujące rekordy w bazie danych.",
            style="bold yellow",
        )
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != "tak":
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()
    elif args.update_signature:
        mode = "update_signature"
        target_signature = args.update_signature
        console.print(
            f"UWAGA: Ta operacja zaktualizuje wpis o sygnaturze '{target_signature}'.",
            style="bold yellow",
        )
        if input("Czy na pewno chcesz kontynuować? (tak/nie): ").lower() != "tak":
            console.print("Operacja anulowana przez użytkownika.", style="bold red")
            exit()

    process_unified_unit(
        mode=mode, target_signature=target_signature, limit_count=limit_count
    )
