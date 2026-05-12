import random
import os
import sys
import json
import sqlite3
import datetime
from loguru import logger

# --- 🛠️ ROBUST PATHING ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
# Pointing strictly to the search query file
WORDLIST_PATH = os.path.join(PROJECT_ROOT, "config", "wordlist.txt")

# Strictly locked to the two active test profiles to manage local hardware
SESSION_METRICS = {
    "Angela_SSO": {"video_count": 0, "ad_count": 0, "organic_count": 0},
    "Michelle_Unique": {"video_count": 0, "ad_count": 0, "organic_count": 0}
}

PERSONA_STATE = {
    "current_persona": None,
    "current_phase": "initialization",
    "start_time": None
}

def generate_dynamic_query(persona_name, platform):
    PERSONA_STATE["current_persona"] = persona_name
    
    if not os.path.exists(WORDLIST_PATH):
        logger.error(f"    [❌] WORDLIST NOT FOUND AT: {WORDLIST_PATH}")
        return "trending fashion"
        
    try:
        with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
            
        if not queries:
            logger.error(f"    [❌] FILE READ AS EMPTY: wordlist.txt has no valid text lines.")
            return "viral makeup trends"
            
        # Use SystemRandom for better entropy to prevent query repetition
        chosen_query = random.SystemRandom().choice(queries)
        logger.info(f"    [🎲] RANDOMIZER: Selected '{chosen_query}' for {persona_name} on {platform}")
        
        # Sniffer logic using json, sqlite3, and datetime can execute here without crashing
        
        return chosen_query
        
    except UnicodeDecodeError:
        logger.error("    [!] Encoding error: wordlist.txt contains non-UTF-8 characters.")
        return "skincare routine"
    except Exception as e:
        logger.error(f"    [!] Error reading wordlist: {e}")
        return "skincare routine"