import asyncio
import random
import time
import sqlite3
import json
from loguru import logger

# Project-specific imports restored
from utils.telemetry import log_telemetry
from core.database_manager import DB_PATH, CURRENT_SESSION_ID, get_db_connection
from utils.shared_data import PERSONA_STATE 
from utils.post_interest import load_interest_trigger_list, is_interested_in

async def determine_video_engagement(persona_name, content_title, platform):
    """
    Generalized Brain: Decides IF to watch, HOW LONG to watch, and IF to like.
    Strictly follows the 5:1 skip ratio and randomized attention span algorithms.
    """
    interests = load_interest_trigger_list(persona_name)
    matched_trigger = next((word for word in interests if word in content_title.lower()), "None")
    is_interested = matched_trigger != "None"

    # --- 🧠 ATTENTION SPAN & ENGAGEMENT ALGORITHM ---
    if is_interested:
        # 1. Interest Match: Always watch 100% and always like
        watch_percent = 1.0
        should_like = True
        logger.info(f"    [🎯] {persona_name}: Interest Match '{matched_trigger}'. Plan: 100% Watch + Like.")
    else:
        # 2. 5:1 Skip Ratio: ~83.3% chance to skip non-interest content
        if random.random() < 0.833:
            logger.debug(f"    [⏭️] {persona_name}: 5:1 Ratio Skip for non-interest content.")
            return False, 0.0, False, "None"
        
        # 3. Randomized Attention Span Mimicry: 10%, 25%, 50%, 75%, or 100%
        watch_percent = random.choice([0.10, 0.25, 0.50, 0.75, 1.0])
        
        # 4. Randomized Likes: 15% chance to like non-interest content
        should_like = random.random() < 0.15
        logger.info(f"    [⏳] {persona_name}: No interest match. Plan: {int(watch_percent*100)}% Watch.")

    # --- 📊 GENERALIZED DB LOGGING ---
    # Recording the view state using WAL connection to prevent multi-tab locks
    try:
        timestamp_ms = int(time.time() * 1000)
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO Post (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (f"vid_{timestamp_ms}", CURRENT_SESSION_ID, persona_name, platform, 
              json.dumps({"text": content_title, "trigger": matched_trigger, "watch_span": watch_percent}), 
              "Video Publisher", "VIDEO_ENGAGEMENT", "WATCHED", 0))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"    [!] Brain DB Log Error (Locked): {e}")

    return is_interested, watch_percent, should_like, matched_trigger