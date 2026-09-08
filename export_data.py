import os
import sys
import sqlite3
import datetime
from pathlib import Path
import pandas as pd
from openpyxl.utils import get_column_letter

import config

def find_database_path():
    candidates = [
        config.DB_FILE,
        "telemetry.db",
        str(Path.home() / "Library" / "Application Support" / "TimerForRadiologist" / "telemetry.db"),
        str(Path(os.getenv('APPDATA', str(Path.home()))) / "TimerForRadiologist" / "telemetry.db"),
        str(Path.home() / ".timer_radiologist" / "telemetry.db"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return config.DB_FILE

def export_to_excel(target_path=None):
    db_path = find_database_path()
    print(f"Connecting to database: {db_path}...")

    try:
        conn = sqlite3.connect(db_path)
        df_timers = pd.read_sql_query("SELECT * FROM timers", conn)
        df_clicks = pd.read_sql_query("SELECT * FROM clicks", conn)
        conn.close()
    except sqlite3.OperationalError as e:
        msg = "Nie znaleziono bazy danych lub tabel. Uruchom najpierw stoper, aby zapisać dane."
        print(msg)
        return False, msg, None
    except Exception as e:
        msg = f"Błąd odczytu bazy danych: {e}"
        print(msg)
        return False, msg, None

    if df_timers.empty and df_clicks.empty:
        msg = "Baza danych jest pusta. Brak danych do eksportu."
        print(msg)
        return False, msg, None

    if target_path is None:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home()
        filename = f"timer_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        target_path = desktop / filename
    else:
        target_path = Path(target_path)

    print(f"Formatting and writing data to Excel: {target_path}...")
    try:
        with pd.ExcelWriter(str(target_path), engine='openpyxl') as writer:
            df_timers.to_excel(writer, sheet_name='Timers', index=False)
            df_clicks.to_excel(writer, sheet_name='Clicks', index=False)
            
            workbook = writer.book
            for sheet_name in workbook.sheetnames:
                worksheet = workbook[sheet_name]
                worksheet.auto_filter.ref = worksheet.dimensions
                for col in worksheet.columns:
                    max_length = 0
                    column_letter = col[0].column_letter
                    for cell in col:
                        try:
                            cell_len = len(str(cell.value))
                            if cell_len > max_length:
                                max_length = cell_len
                        except Exception:
                            pass
                    adjusted_width = max_length + 2
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        success_msg = f"Dane zostały pomyślnie wyeksportowane do: {target_path}"
        print(success_msg)
        return True, success_msg, str(target_path)
    except Exception as e:
        err_msg = f"Błąd zapisu pliku Excel: {e}"
        print(err_msg)
        return False, err_msg, None

if __name__ == "__main__":
    success, msg, path = export_to_excel()
