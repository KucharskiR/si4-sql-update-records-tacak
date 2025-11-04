
import os
import pyodbc
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from datetime import datetime

# Inicjalizacja konsoli Rich
console = Console()

def get_sql_from_file(file_path):
    """Odczytuje treść zapytania SQL z pliku."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        console.print(f"[bold red]Błąd: Nie znaleziono pliku SQL: {file_path}[/bold red]")
        return None

def get_db_connection():
    """Nawiązuje i zwraca połączenie z bazą danych."""
    load_dotenv()
    db_server = os.getenv("DB_SERVER")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not db_server or not db_name:
        console.print("[bold red]Błąd: Zmienne środowiskowe DB_SERVER i DB_NAME muszą być ustawione w pliku .env.[/bold red]")
        return None

    try:
        if db_user and db_password:
            # SQL Server Authentication
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={db_password}"
        else:
            # Windows Authentication
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};Trusted_Connection=yes;"
        
        return pyodbc.connect(conn_str)
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        console.print(f"[bold red]Błąd połączenia z bazą danych: {sqlstate}[/bold red]")
        console.print(ex)
        return None

def fetch_data_to_update(cursor, start_date, end_date):
    """Pobiera wpisy RCP do aktualizacji z podanego zakresu dat."""
    query = """
    SELECT
        WFD_ID,
        WFD_AttText7 as 'ID_Pracownika',
        WFD_AttDateTime10 as 'Dzien_Roboczy',
        WFD_AttText9 as 'Jednostka_Organizacyjna',
        WFD_AttText8 as 'Kod_Jednostki_Organizacyjnej',
        WFD_AttDecimal3 as 'Laczny_Czas'
    FROM WFElements
    WHERE
        WFD_DTYPEID = '56'
        AND WFD_AttDateTime10 >= ?
        AND WFD_AttDateTime10 <= ?
        AND (
            WFD_AttText9 IS NULL OR WFD_AttText9 = '' OR
            WFD_AttText8 IS NULL OR WFD_AttText8 = '' OR
            WFD_AttDecimal3 IS NULL
        )
    """
    cursor.execute(query, start_date, end_date)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_new_values(cursor, employee_id, work_date, wfd_id):
    """Pobiera nowe wartości dla jednostki, kodu jednostki i łącznego czasu."""
    
    # Pobranie zapytań z plików
    unit_sql = get_sql_from_file('resources/get_employee_unit.sql')
    unit_code_sql = get_sql_from_file('resources/get_employee_unit_code.sql')
    total_time_sql = "SELECT SUM(DET_Value1) FROM WFElementDetails WHERE DET_WFDID = ?"

    new_unit, new_unit_code, new_total_time = None, None, None

    # Pobranie nowej jednostki organizacyjnej
    if unit_sql:
        query = unit_sql.replace("#{Numer_teczki_pracownika}#", f"'{employee_id}'").replace("#{Data_dnia_roboczego}#", f"'{work_date}'")
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            new_unit = result[0]

    # Pobranie nowego kodu jednostki
    if unit_code_sql:
        query = unit_code_sql.replace("#{Numer_teczki_pracownika}#", f"'{employee_id}'").replace("#{Data_dnia_roboczego}#", f"'{work_date}'")
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            new_unit_code = result[0]

    # Pobranie łącznego czasu
    cursor.execute(total_time_sql, wfd_id)
    result = cursor.fetchone()
    if result and result[0] is not None:
        new_total_time = float(result[0])

    return new_unit, new_unit_code, new_total_time


def main():
    parser = argparse.ArgumentParser(description="Aktualizuje wpisy RCP o brakujące dane.")
    parser.add_argument('--start-date', required=True, help="Data początkowa w formacie DD.MM.RRRR")
    parser.add_argument('--end-date', required=True, help="Data końcowa w formacie DD.MM.RRRR")
    parser.add_argument('--update', action='store_true', help="Uruchamia tryb aktualizacji danych w bazie.")
    args = parser.parse_args()

    try:
        start_date_dt = datetime.strptime(args.start_date, "%d.%m.%Y")
        end_date_dt = datetime.strptime(args.end_date, "%d.%m.%Y")
    except ValueError:
        console.print("[bold red]Błąd: Daty muszą być w formacie DD.MM.RRRR.[/bold red]")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        console.print(f"Pobieranie wpisów RCP od {args.start_date} do {args.end_date}...")
        records_to_process = fetch_data_to_update(cursor, start_date_dt, end_date_dt)
        
        if not records_to_process:
            console.print("[green]Nie znaleziono wpisów do aktualizacji w podanym zakresie dat.[/green]")
            return

        console.print(f"Znaleziono {len(records_to_process)} wpisów do przetworzenia. Analiza danych...")

        updates = []
        with Progress() as progress:
            task = progress.add_task("[cyan]Analizowanie wpisów...", total=len(records_to_process))
            for rec in records_to_process:
                new_unit, new_unit_code, new_total_time = get_new_values(cursor, rec['ID_Pracownika'], rec['Dzien_Roboczy'], rec['WFD_ID'])
                
                # Sprawdzamy, czy jest cokolwiek do zaktualizowania
                if new_unit != rec['Jednostka_Organizacyjna'] or new_unit_code != rec['Kod_Jednostki_Organizacyjnej'] or (new_total_time is not None and new_total_time != rec['Laczny_Czas']):
                    updates.append({
                        "WFD_ID": rec['WFD_ID'],
                        "ID_Pracownika": rec['ID_Pracownika'],
                        "Dzien_Roboczy": rec['Dzien_Roboczy'].strftime('%Y-%m-%d'),
                        "old_unit": rec['Jednostka_Organizacyjna'], "new_unit": new_unit,
                        "old_unit_code": rec['Kod_Jednostki_Organizacyjnej'], "new_unit_code": new_unit_code,
                        "old_total_time": rec['Laczny_Czas'], "new_total_time": new_total_time
                    })
                progress.update(task, advance=1)

        if not updates:
            console.print("[green]Wszystkie wpisy w podanym zakresie są aktualne. Brak zmian do wykonania.[/green]")
            return

        # Wyświetlanie tabeli zmian
        table = Table(title="Podsumowanie zmian")
        table.add_column("WFD_ID", style="cyan")
        table.add_column("Pracownik", style="magenta")
        table.add_column("Data", style="yellow")
        table.add_column("Pole", style="bold")
        table.add_column("Stara wartość", style="red")
        table.add_column("Nowa wartość", style="green")

        for u in updates:
            if u['old_unit'] != u['new_unit']:
                table.add_row(str(u['WFD_ID']), u['ID_Pracownika'], u['Dzien_Roboczy'], "Jednostka Org.", str(u['old_unit']), str(u['new_unit']))
            if u['old_unit_code'] != u['new_unit_code']:
                table.add_row(str(u['WFD_ID']), u['ID_Pracownika'], u['Dzien_Roboczy'], "Kod Jednostki", str(u['old_unit_code']), str(u['new_unit_code']))
            if u['old_total_time'] != u['new_total_time'] and u['new_total_time'] is not None:
                 table.add_row(str(u['WFD_ID']), u['ID_Pracownika'], u['Dzien_Roboczy'], "Łączny czas", f"{u['old_total_time']:.4f}" if u['old_total_time'] is not None else "None", f"{u['new_total_time']:.4f}" if u['new_total_time'] is not None else "None")

        console.print(table)

        if args.update:
            console.print(f"\n[bold yellow]Znaleziono {len(updates)} zmian do wprowadzenia.[/bold yellow]")
            if console.input("Czy na pewno chcesz zaktualizować te wpisy w bazie danych? (y/n): ").lower() == 'y':
                
                update_query = """
                UPDATE WFElements
                SET WFD_AttText9 = ?, WFD_AttText8 = ?, WFD_AttDecimal3 = ?
                WHERE WFD_ID = ?
                """
                
                with Progress() as progress:
                    task = progress.add_task("[cyan]Aktualizowanie bazy danych...", total=len(updates))
                    for u in updates:
                        # Używamy nowych wartości, ale jeśli któraś jest None, zachowujemy starą, chyba że stara też jest None.
                        final_unit = u['new_unit'] if u['new_unit'] is not None else u['old_unit']
                        final_unit_code = u['new_unit_code'] if u['new_unit_code'] is not None else u['old_unit_code']
                        final_total_time = u['new_total_time'] if u['new_total_time'] is not None else u['old_total_time']
                        
                        cursor.execute(update_query, final_unit, final_unit_code, final_total_time, u['WFD_ID'])
                        progress.update(task, advance=1)
                
                conn.commit()
                console.print("\n[bold green]Aktualizacja zakończona pomyślnie![/bold green]")
            else:
                console.print("[bold red]Aktualizacja anulowana przez użytkownika.[/bold red]")
        else:
            console.print("\n[bold cyan]Uruchomiono w trybie 'na sucho'. Aby zapisać zmiany w bazie, użyj flagi --update.[/bold cyan]")

    except pyodbc.Error as ex:
        console.print(f"[bold red]Wystąpił błąd SQL:[/bold red]")
        console.print(ex)
    finally:
        if conn:
            conn.close()
            console.print("Połączenie z bazą danych zostało zamknięte.")


if __name__ == "__main__":
    main()
