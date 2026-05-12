import sqlite3
import os
import uuid
from loguru import logger

# --- PATHING ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "results", "silo_audit.db")

# Generate a unique ID for this specific simulation cycle
CURRENT_SESSION_ID = f"run_{str(uuid.uuid4())[:8]}"

def get_db_connection():
    """
    Returns a thread-safe connection with a 30s timeout.
    WAL mode is assumed to be set globally by init_db().
    """
    # SQLite timeout parameter is natively a float (seconds)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    
    # Synchronous NORMAL is safe to set per-connection and highly recommended for WAL
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    # Explicitly set the busy timeout at the pragma level as a fallback (milliseconds)
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn

def init_db():
    """Initializes the relational schema and globally sets WAL mode."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Open a basic connection just for initialization
    conn = sqlite3.connect(DB_PATH)
    
    # Set WAL mode ONCE here. It is persistent in the database file.
    # This requires an exclusive lock, so doing it during init prevents runtime contention.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    cursor = conn.cursor()
    
    # Full Post table schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS Post (
        id INTEGER PRIMARY KEY,
        pk_id TEXT UNIQUE,
        session_id TEXT,
        persona_name TEXT,
        platform TEXT,
        content_text TEXT,
        source_author TEXT,
        event_type TEXT,
        interaction_state TEXT,
        is_ad BOOLEAN,
        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Full Interpretation table schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS Interpretation (
        id INTEGER PRIMARY KEY,
        pk_id TEXT,
        score INTEGER,
        theme TEXT,
        reasoning TEXT,
        FOREIGN KEY (pk_id) REFERENCES Post (pk_id)
    )''')

    # Full ReliabilityInterpretation table schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS ReliabilityInterpretation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pk_id TEXT,
        score INTEGER,
        theme TEXT,
        reasoning TEXT,
        session INTEGER, 
        interpreted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pk_id) REFERENCES Post (pk_id)
    )''')

    # Full SessionLog table schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS SessionLog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        persona TEXT,
        platform TEXT,
        status TEXT,
        action TEXT,
        target TEXT
    )''')

    conn.commit()
    conn.close()
    logger.info("Relational database fully initialized. WAL mode set persistently.")