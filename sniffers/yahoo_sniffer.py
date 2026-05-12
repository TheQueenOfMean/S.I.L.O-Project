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
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.telemetry import log_telemetry  # RESTORED

async def sniff_yahoo(response, persona_name):
    """Intercepts Yahoo Feed and Search to monitor algorithmic drift."""
    url = response.url.lower()
    state = PERSONA_STATE.get(persona_name, {})
    q = state.get("current_query", "Organic")

    if "yahoo.com" in url and any(x in url for x in ["graphql", "stream", "api", "r.search.yahoo"]):
        try:
            is_click = "r.search.yahoo" in url
            ts = int(time.time() * 1000)
            
            if is_click:
                event_type = "CLICK_INTERACTION"
                data = {"url": url, "text": f"Outbound Search Click: {url[:100]}"}
            else:
                json_data = await response.json()
                items = []
                def traverse(n, ad=False):
                    if isinstance(n, dict):
                        is_ad = ad or n.get("is_ad") == 1 or n.get("type") == "ad"
                        txt = n.get("title") or n.get("summary")
                        if txt and isinstance(txt, str) and len(txt) > 5:
                            items.append({"title": txt, "is_ad": 1 if is_ad else 0})
                        for v in n.values(): traverse(v, is_ad)
                    elif isinstance(n, list): 
                        for v in n: traverse(v, ad)
                traverse(json_data)
                event_type = "ALGO_RECOMMENDATION"
                data = {"items": items}

            conn = sqlite3.connect(DB_PATH)
            conn.execute('''
                INSERT OR IGNORE INTO Post 
                (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) 
                VALUES (?,?,?,?,?,?,?,?,?)
            ''', (f"yh_{ts}", CURRENT_SESSION_ID, persona_name, "Yahoo", 
                 json.dumps({"query": q, "data": data}), "Yahoo Sniffer", event_type, "VIEWED", 0))
            conn.commit()
            conn.close()
            
            _save_timeline(persona_name, "yahoo", event_type, data)
            log_telemetry(persona_name, "Yahoo", "SNIFF_SUCCESS", action=event_type)
        except Exception: 
            pass

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