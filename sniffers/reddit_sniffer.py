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

async def intercept_reddit_feed(response, persona_name):
    """Intercepts Reddit GQL/API to analyze drift in recommendations."""
    url = response.url.lower()
    if any(x in url for x in ["gql.reddit.com", "oauth.reddit.com", "reddit.com/api"]):
        try:
            if "json" not in response.headers.get("content-type", "").lower(): 
                return
            
            json_data = await response.json()
            interests = load_interest_trigger_list(persona_name)
            is_sso = "_sso" in persona_name.lower()
            ts = int(time.time() * 1000)
            posts = []
            
            def traverse(node, is_ad_context=False):
                if isinstance(node, dict):
                    current_ad = is_ad_context or any(node.get(k) is True for k in ["isSponsored", "promoted"])
                    title = node.get("title") or node.get("postTitle")
                    if title and isinstance(title, str) and len(title) > 5:
                        matched = next((w for w in interests if w in title.lower()), "None")
                        posts.append({"title": title, "matched": matched, "is_ad": 1 if current_ad else 0})
                    for v in node.values(): 
                        traverse(v, current_ad)
                elif isinstance(node, list): 
                    for v in node:
                        traverse(v, is_ad_context)
            
            traverse(json_data)
            if posts:
                conn = sqlite3.connect(DB_PATH)
                for i, post in enumerate(posts):
                    event = "INTEREST_MATCH" if post['matched'] != "None" else "ALGO_RECOMMENDATION"
                    conn.execute('''
                        INSERT OR IGNORE INTO Post 
                        (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) 
                        VALUES (?,?,?,?,?,?,?,?,?)
                    ''', (f"rd_{ts}_{i}", CURRENT_SESSION_ID, persona_name, "Reddit", 
                        post['title'][:400], "Reddit API", event, "VIEWED", post["is_ad"]))
                conn.commit()
                conn.close()
                
                _save_timeline(persona_name, "reddit", "ALGO_RECOMMENDATION", {"posts": posts})
                log_telemetry(persona_name, "Reddit", "SNIFF_SUCCESS", action="Feed_Intercept")
        except Exception as e: 
            logger.error(f"Reddit Sniffer Error: {e}")

def _save_timeline(persona_name, folder, event_type, data):
    """Categorizes JSON by platform subfolder with persona metadata."""
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