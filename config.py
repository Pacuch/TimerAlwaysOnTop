# Configuration settings

# Set to True to enable debug print statements in the terminal
DEBUG = False

import datetime

# Database and export file paths
DB_FILE = "telemetry.db"
EXPORT_FILE = f"timer_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
