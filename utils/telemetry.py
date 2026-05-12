import os
import sys
import sqlite3
from datetime import datetime
from loguru import logger
from core.database_manager import DB_PATH, get_db_connection

# --- 📂 LOCAL ROOT ACCESS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def _init_telemetry_table():
    """Ensures the telemetry table exists in the main S.I.L.O. database."""
    try:
        # Safely using the context manager for init
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS SessionLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                persona TEXT,
                platform TEXT,
                status TEXT,
                action TEXT,
                target TEXT
            )''')
            # Context manager auto-commits upon successful exit
    except Exception as e:
        logger.error(f"Telemetry Table Init Error: {e}")

def log_session(persona, platform, status, action="Interaction", target="N/A"):
    """Standard session logger for human-like interactions."""
    _write_to_db(persona, platform, status, action, target)

def log_telemetry(persona, platform, status, action="Automation", target="N/A"):
    """Specifically for automated events like AI CAPTCHA solves."""
    _write_to_db(persona, platform, status, action, target)

def _write_to_db(persona, platform, status, action, target):
    """Internal helper to insert records into SQLite with high-concurrency safety."""
    try:
        # Using 'with' on the connection auto-commits if successful, 
        # or auto-rolls back if an error occurs. The connection cleanly 
        # closes the moment you exit the 'with' block.
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO SessionLog (timestamp, persona, platform, status, action, target)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), persona, platform, status, action, str(target)))
            
    except Exception as e:
       # Graceful logging to console if the DB is under extreme pressure
       logger.error(f"SQLite Telemetry Write Error (Locked): {e}")