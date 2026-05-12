import os
import sys
import asyncio
import gc
import time
from loguru import logger 

# Failsafe: Ensures Python recognizes your root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import run_persona_session
from core.database_manager import init_db

# S.I.L.O. Testing Personas
ANGELA = {"name": "Angela_SSO", "path": "sessions/angela_sso_v2", "sso": True}
MICHELLE = {"name": "Michelle_Unique", "path": "sessions/michelle_unique_v2", "sso": False}

async def execute_simulation(mode):
    start_time = time.time()
    try:
        init_db()
        logger.success("[⚙️] Master SQLite Database initialized.")
    except Exception as e:
        logger.warning(f"[!] DB Initialization Error: {e}")

    if mode in ["1", "3"]:
        logger.info(f" [🧪] COLLECTING DATA (HEADLESS): {ANGELA['name']}")
        # Explicitly enforcing headless mode for the master run
        await run_persona_session(ANGELA, minutes=30, headless=True) 
        gc.collect()
        await asyncio.sleep(10)

    if mode in ["2", "3"]:
        logger.info(f" [🧪] COLLECTING DATA (HEADLESS): {MICHELLE['name']}")
        # Explicitly enforcing headless mode for the master run
        await run_persona_session(MICHELLE, minutes=30, headless=True)

    logger.info("\n [🛑] DATA COLLECTION COMPLETE.")
    logger.success(f" Total Runtime: {(time.time() - start_time) / 60:.2f}m")

if __name__ == "__main__":
    print("\n" + "="*45)
    print(" S.I.L.O. RESEARCH ORCHESTRATOR ")
    print("="*45)
    print("1: Angela Only (SSO Profile)")
    print("2: Michelle Only (Unique Profile)")
    print("3: Full Run (Both Personas)")
    print("q: Quit")
    print("="*45)
    
    # Bulletproof loop: Traps the terminal until a valid input is received
    while True:
        choice = input("\nSelect Mode (1/2/3/q): ").strip().lower()
        
        if choice == 'q':
            print("Exiting...")
            break
        elif choice in ["1", "2", "3"]:
            asyncio.run(execute_simulation(choice))
            break
        else:
            print("[!] Invalid input. Please type 1, 2, 3, or q and press Enter.")