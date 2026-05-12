import os, json, time, sqlite3, sys
from datetime import datetime
from loguru import logger

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from utils.shared_data import PERSONA_STATE
from utils.google_utils import extract_google_text
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.telemetry import log_telemetry  # RESTORED

async def sniff_google(response, persona_name):
    try:
        url = response.url.lower()
        state = PERSONA_STATE.get(persona_name, {})
        q = state.get("current_query", "Organic")
        
        is_click = any(x in url for x in ["/url?", "/aclk", "/adurl"])
        is_result = any(x in url for x in ["/search?", "news.google.com"]) and not is_click
        if not (is_click or is_result) or any(trig in url for trig in ["/collect", "/telemetry"]): return

        ts = int(time.time() * 1000)
        is_ad = 1 if ("aclk" in url or "adurl" in url) else 0
        
        if is_click:
            content = f"Network Click: {url[:300]}"
            event_type = "CLICK_INTERACTION"
        else:
            try:
                body = (await response.body()).decode('utf-8', errors='ignore')
                raw_text = extract_google_text(body)
                content = f"{raw_text[:2000]}"
                event_type = "SEARCH_RESULT"
                if "Sponsored" in body: is_ad = 1
            except: return

        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO Post (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) VALUES (?,?,?,?,?,?,?,?,?)',
                     (f"gg_{ts}", CURRENT_SESSION_ID, persona_name, "Google", content, "Google Sniffer", event_type, "VIEWED", is_ad))
        conn.commit(); conn.close()
        
        _save_timeline(persona_name, "google", event_type, {"query": q, "content": content, "url": url})
        log_telemetry(persona_name, "Google", "SNIFF_SUCCESS", action=event_type)
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