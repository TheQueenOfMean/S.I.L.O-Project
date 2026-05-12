import os
import json
import time
import sqlite3
import sys
from datetime import datetime
from loguru import logger

# --- 🛠️ ROBUST PATHING ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.shared_data import PERSONA_STATE
from utils.post_interest import load_interest_trigger_list
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.telemetry import log_telemetry  # RESTORED

async def intercept_x_feed(response, persona_name):
    """Intercepts X Timelines to track personalized content pushed to users."""
    url = response.url
    if any(x in url for x in ["HomeTimeline", "HomeLatestTimeline", "SearchTimeline"]):
        try:
            json_data = await response.json()
            ts = int(time.time() * 1000)
            interests = load_interest_trigger_list(persona_name)
            is_sso = "_sso" in persona_name.lower()

            tweets = []
            def traverse(node, is_ad=False):
                if isinstance(node, dict):
                    ad = is_ad or 'promotedmetadata' in str(node).lower()
                    text = node.get("full_text") or node.get("text")
                    if text and len(str(text)) > 5:
                        matched = next((w for w in interests if w in str(text).lower()), "None")
                        tweets.append({"text": text, "matched": matched, "is_ad": 1 if ad else 0})
                    for v in node.values(): 
                        traverse(v, ad)
                elif isinstance(node, list): 
                    for v in node:
                        traverse(v, is_ad)
            
            traverse(json_data)
            if tweets:
                conn = sqlite3.connect(DB_PATH)
                for i, tw in enumerate(tweets):
                    event = "INTEREST_MATCH" if tw['matched'] != "None" else "ALGO_RECOMMENDATION"
                    conn.execute('''
                        INSERT OR IGNORE INTO Post 
                        (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) 
                        VALUES (?,?,?,?,?,?,?,?,?)
                    ''', (f"x_{ts}_{i}", CURRENT_SESSION_ID, persona_name, "X Timeline", 
                        tw['text'][:400], "X API", event, "VIEWED", tw["is_ad"]))
                conn.commit()
                conn.close()
                
                _save_timeline(persona_name, "x", "ALGO_RECOMMENDATION", {"tweets": tweets})
                log_telemetry(persona_name, "X", "SNIFF_SUCCESS", action="Timeline_Audit")
        except Exception as e: 
            logger.error(f"X Sniffer Error: {e}")

def _save_timeline(persona_name, folder, event_type, data):
    data_dir = os.path.join(PROJECT_ROOT, "data", folder)
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{folder}_Timeline.json")
    is_sso = "_sso" in persona_name.lower()
    entry = {"timestamp": datetime.now().isoformat(), "session_id": CURRENT_SESSION_ID, "persona_name": persona_name, "is_sso": is_sso, "event_type": event_type, "data": data}
    history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: history = json.load(f)
        except: pass
    history.append(entry)
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(history, f, indent=4)