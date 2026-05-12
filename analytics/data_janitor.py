import sqlite3
import os
import sys
from loguru import logger

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database_manager import DB_PATH

def scrub_silo_database():
    if not os.path.exists(DB_PATH):
        logger.error(f" [!] Data Janitor failed: Database not found at {DB_PATH}")
        return

    logger.info(" [🧹] Data Janitor: Initializing intra-session S.I.L.O. scrub...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Post")
        before_count = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # INTRA-SESSION DEDUPLICATION LOGIC
        # Groups by session_id AND content_text. 
        # If the same post appears in run_A and run_B, both are kept.
        # If the same post appears twice in run_A, the clone is killed.
        # ---------------------------------------------------------
        cursor.execute('''
            DELETE FROM Post 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM Post 
                GROUP BY session_id, persona_name, platform, content_text
            )
        ''')
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM Post")
        after_count = cursor.fetchone()[0]
        deleted_rows = before_count - after_count
        
        logger.success(f" [✨] Data Janitor Complete: Vaporized {deleted_rows} intra-session clones.")
        logger.info(f" [📊] Accumulated dataset: {after_count} unique items preserved across all historical runs.")
        
        conn.close()
        
    except Exception as e:
        logger.error(f" [!] Database scrub failed: {e}")

if __name__ == "__main__":
    scrub_silo_database()