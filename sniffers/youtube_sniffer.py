import os, json, time, sqlite3, sys
from datetime import datetime
from loguru import logger

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from utils.post_interest import load_interest_trigger_list
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.telemetry import log_telemetry  # RESTORED

async def intercept_youtube_feed(response, persona_name):
    if any(endpoint in response.url for endpoint in ["youtubei/v1/browse", "youtubei/v1/search"]):
        try:
            json_data = await response.json()
            interests = load_interest_trigger_list(persona_name)
            videos = []
            
            def traverse(node):
                if isinstance(node, dict):
                    if "title" in node and isinstance(node["title"], dict):
                        txt = node["title"].get("simpleText") or "".join(r.get("text", "") for r in node["title"].get("runs", []))
                        if txt:
                            ad = 1 if 'adplacement' in str(node).lower() or 'promoted' in str(node).lower() else 0
                            matched = next((w for w in interests if w in txt.lower()), "None")
                            videos.append({"title": txt, "matched": matched, "is_ad": ad})
                    for v in node.values(): traverse(v)
                elif isinstance(node, list): 
                    for v in node: traverse(v)
            
            traverse(json_data)
            if videos:
                conn = sqlite3.connect(DB_PATH)
                ts = int(time.time() * 1000)
                for i, v in enumerate(videos):
                    conn.execute('INSERT INTO Post (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad) VALUES (?,?,?,?,?,?,?,?,?)',
                                (f"yt_{ts}_{i}", CURRENT_SESSION_ID, persona_name, "YouTube", v['title'], "YouTube API", "ALGO_RECOMMENDATION", "VIEWED", v['is_ad']))
                conn.commit(); conn.close()
                _save_timeline(persona_name, "youtube", "ALGO_RECOMMENDATION", {"videos": videos})
                log_telemetry(persona_name, "YouTube", "SNIFF_SUCCESS", action="Feed_Audit")
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