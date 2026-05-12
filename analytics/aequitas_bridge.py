import os
import sys
import sqlite3
import pandas as pd
from loguru import logger
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database_manager import DB_PATH

def run_behavioral_audit():
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}. Run test_run.py first.")
        return

    logger.info("[📊] Phase 5: Generating Aequitas Behavioral Bridge...")
    conn = sqlite3.connect(DB_PATH)

    try:
        # TWEAK: Consolidated platforms to perfectly match the 6 Sniffer names
        query = '''
            SELECT 
                session_id,
                persona_name, 
                CASE 
                    WHEN platform LIKE '%Google%' THEN 'Google'
                    WHEN platform LIKE '%Yahoo%' THEN 'Yahoo'
                    WHEN platform LIKE '%TikTok%' OR platform LIKE '%Tiktok%' THEN 'TikTok'
                    WHEN platform LIKE '%YouTube%' OR platform LIKE '%Youtube%' THEN 'YouTube'
                    WHEN platform LIKE '%Reddit%' THEN 'Reddit'
                    WHEN platform LIKE '%X%' OR platform LIKE '%Twitter%' THEN 'X Timeline'
                    ELSE platform
                END as platform_normalized,
                COUNT(*) as total_items,
                SUM(CASE WHEN is_ad = 1 OR event_type = 'TARGETED_AD' THEN 1 ELSE 0 END) as targeted_ads,
                SUM(CASE WHEN interaction_state = 'CLICKED' OR event_type LIKE '%CLICK%' THEN 1 ELSE 0 END) as active_clicks,
                COUNT(DISTINCT source_author) as unique_authors_encountered
            FROM Post
            GROUP BY session_id, persona_name, platform_normalized
        '''
        df = pd.read_sql_query(query, conn)

        if df.empty:
            logger.warning("No data found in Post table to summarize.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        report_dir = os.path.join(PROJECT_ROOT, "results", "reports")
        os.makedirs(report_dir, exist_ok=True)
        
        # Rename column back to 'platform' for a clean CSV header
        df.rename(columns={'platform_normalized': 'platform'}, inplace=True)
        
        csv_path = os.path.join(report_dir, f"silo_behavioral_matrix_{timestamp}.csv")
        df.to_csv(csv_path, index=False)
        
        print("\n" + "="*60)
        print(" AEQUITAS BEHAVIORAL & ECHO CHAMBER SUMMARY")
        print("="*60)
        print(df.to_string(index=False))
        print("="*60)
        
        logger.success(f"Behavioral matrix saved: {csv_path}")

    except Exception as e:
        logger.error(f"Failed to bridge data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_behavioral_audit()