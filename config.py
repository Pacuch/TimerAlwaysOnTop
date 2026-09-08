import os
import sys
from pathlib import Path
import datetime

# Set to True to enable debug print statements in the terminal
DEBUG = False

def get_db_path():
    # If running as a frozen application (PyInstaller macOS .app / Windows .exe)
    if getattr(sys, 'frozen', False):
        if sys.platform == "darwin":
            app_dir = Path.home() / "Library" / "Application Support" / "TimerForRadiologist"
        elif sys.platform == "win32":
            app_dir = Path(os.getenv('APPDATA', str(Path.home()))) / "TimerForRadiologist"
        else:
            app_dir = Path.home() / ".timer_radiologist"
        app_dir.mkdir(parents=True, exist_ok=True)
        return str(app_dir / "telemetry.db")
    return "telemetry.db"

# Database and export file paths
DB_FILE = get_db_path()
EXPORT_FILE = f"timer_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
