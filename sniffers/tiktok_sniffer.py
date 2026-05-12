import os, json, time, sqlite3, sys
from datetime import datetime
from loguru import logger

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from utils.post_interest import load_interest_trigger_list
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.telemetry import log_telemetry  # RESTORED

async def intercept_tiktok_feed(response, persona_name):
    url = response.url.lower()
    if "/api/recommend/item_list" in url:
        try:
            json_data = await response.json()
            items = json_data.get("itemList", [])
            if not items: return
            
            interests = load_interest_trigger_list(persona_name)
            captured = []
            conn = sqlite3.connect(DB_PATH)
            ts = int(time.time() * 1000)
            
            for i, item in enumerate(items):
                desc = item.get("desc", "No Description")
                matched = next((w for w in interests if w in desc.lower()), "None")
                captured.append({"desc": desc, "matched": matched})
                
                conn.execute('INSERT INTO Post (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) VALUES (?,?,?,?,?,?,?,?,?)',
                            (f"tk_{ts}_{i}", CURRENT_SESSION_ID, persona_name, "TikTok", desc, "TikTok API", "ALGO_RECOMMENDATION", "VIEWED", 0))
            
            conn.commit(); conn.close()
            _save_timeline(persona_name, "tiktok", "ALGO_RECOMMENDATION", {"recommendations": captured})
            log_telemetry(persona_name, "TikTok", "SNIFF_SUCCESS", action="Feed_Intercept")
        except: pass

def _save_timeline(persona_name, folder, event_type, data):
    data_dir = os.path.join(PROJECT_ROOT, "data", folder)
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{folder}_Timeline.json")
    entry = {"timestamp": datetime.now().isoformat(), "session_id": CURRENT_SESSION_ID, "persona_name": persona_name, "is_sso": "_sso" in persona_name.lower(), "event_type": event_type, "data": data}
    history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: history = json.load(f)
        except: pass
    history.append(entry)
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(history, f, indent=4)