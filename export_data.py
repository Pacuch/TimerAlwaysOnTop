import sqlite3
import pandas as pd
from openpyxl.utils import get_column_letter

import config

DB_FILE = config.DB_FILE
EXPORT_FILE = config.EXPORT_FILE

def export_to_excel():
    print(f"Connecting to {DB_FILE}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Load tables into pandas DataFrames
        df_timers = pd.read_sql_query("SELECT * FROM timers", conn)
        df_clicks = pd.read_sql_query("SELECT * FROM clicks", conn)
        conn.close()
    except sqlite3.OperationalError:
        print("No database found yet. Run the main timer app first to generate data.")
        return
    except Exception as e:
        print(f"Error reading database: {e}")
        return

    if df_timers.empty and df_clicks.empty:
        print("Database is empty. Nothing to export.")
        return

    print("Formatting and writing data to Excel...")
    
    # Use pandas ExcelWriter with openpyxl engine to allow formatting
    with pd.ExcelWriter(EXPORT_FILE, engine='openpyxl') as writer:
        df_timers.to_excel(writer, sheet_name='Timers', index=False)
        df_clicks.to_excel(writer, sheet_name='Clicks', index=False)
        
        workbook = writer.book
        
        # Apply formatting to both sheets
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            
            # Enable Excel Filters on the header row for all columns
            worksheet.auto_filter.ref = worksheet.dimensions
            
            # Auto-adjust column widths based on maximum content length
            for col in worksheet.columns:
                max_length = 0
                column_letter = col[0].column_letter # Get the column letter (e.g. 'A', 'B')
                
                for cell in col:
                    try:
                        # Find the longest string in the column
                        cell_len = len(str(cell.value))
                        if cell_len > max_length:
                            max_length = cell_len
                    except:
                        pass
                
                # Apply width + a little extra padding
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
                
    print(f"Success! Data has been exported to: {EXPORT_FILE}")

if __name__ == "__main__":
    export_to_excel()
