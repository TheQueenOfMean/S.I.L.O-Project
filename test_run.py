import asyncio
import os
import sys
import gc
import time
from loguru import logger

# --- PATH INJECTOR ---
# Force Python to recognize the root directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Dynamically import your core engine and database initialization
from core.database_manager import init_db
from core.engine import run_persona_session

# --- CONFIGURATION ---
# 15 minutes per persona = 30 minute total test
TEST_RUNTIME_MINUTES = 15 

PERSONA_CONFIG = {
    "1": {
        "name": "Angela_SSO", 
        "path": "sessions/angela_sso_v2", 
        "sso": True
    },
    "2": {
        "name": "Michelle_Unique", 
        "path": "sessions/michelle_unique_v2", 
        "sso": False
    }
}

async def main():
    start_time = time.time()
    logger.info("="*60)
    logger.info(f" 🧪 S.I.L.O. SMOKE TEST SEQUENCE ({TEST_RUNTIME_MINUTES * 2} MIN TOTAL) ")
    logger.info("="*60)
    
    # 1. Initialize the SQLite Telemetry Database
    try:
        init_db()
        logger.success("[⚙️] Master SQLite Database initialized and ready.")
    except Exception as e:
        logger.warning(f"[!] DB Initialization Error: {e}")
    
    # 2. Run the Experimental Group (Angela)
    logger.info(f"\n[🚀] Starting {TEST_RUNTIME_MINUTES}-minute HEADED test session for Angela_SSO...")
    # headless=False forces the browser to open visibly on your screen
    await run_persona_session(PERSONA_CONFIG["1"], minutes=TEST_RUNTIME_MINUTES, headless=False)
    
    # 3. Flush RAM (Crucial for Playwright stability between profiles)
    logger.info(" [🧹] Flushing RAM for Control Group transition...")
    gc.collect()
    await asyncio.sleep(10)

    # 4. Run the Control Group (Michelle)
    logger.info(f"\n[🚀] Starting {TEST_RUNTIME_MINUTES}-minute HEADED test session for Michelle_Unique...")
    # headless=False forces the browser to open visibly on your screen
    await run_persona_session(PERSONA_CONFIG["2"], minutes=TEST_RUNTIME_MINUTES, headless=False)

    # 5. Final Completion Message
    logger.info("\n[🏁] Data Collection Phase Complete.")
    
    total_time = (time.time() - start_time) / 60
    logger.success(f"\n✅ 30-MINUTE TEST RUN COMPLETE! (Actual Runtime: {total_time:.2f}m)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("\n[🛑] Test run manually aborted by user.")
        sys.exit(0)