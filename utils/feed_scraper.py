import asyncio
import json
import os
import sqlite3
from datetime import datetime
from loguru import logger

# --- 🛠️ ROBUST PATHING ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

from core.platforms.registry import DOM_MAP
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from utils.shared_data import SESSION_METRICS
from utils.telemetry import log_telemetry

class Scraper:
    def __init__(self):
        self.report_dir = os.path.join(PROJECT_ROOT, "results", "reports", "Drift_Reports")
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir, exist_ok=True)

    def _get_platform_folder(self, plt_name):
        p = plt_name.lower()
        if "google" in p: return "google"
        if "yahoo" in p: return "yahoo"
        if "tiktok" in p: return "tiktok"
        if "x timeline" in p or "twitter" in p or "x" == p: return "x"
        if "reddit" in p: return "reddit"
        if "youtube" in p: return "youtube"
        return "other"

    async def scrape_feed_metadata(self, page, p_name, plt_name):
        """Visual auditor for DOM-level content. Safely handles closed pages."""
        # 🛡️ Bulletproof check before interacting
        if page.is_closed():
            logger.debug(f"    [~] Scraper skipped: Page closed for {p_name}.")
            return []

        if plt_name not in DOM_MAP: 
            return []
            
        sel = DOM_MAP[plt_name]
        raw_selector = sel.get("feed_text", sel.get("result_link", "h3"))
        safe_selector = raw_selector.replace(" >> visible=true", "")
        
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass # Graceful timeout continuation
            
        await asyncio.sleep(2)
        if page.is_closed(): return []
        
        try:
            elements = await page.locator(safe_selector).all()
            captured_data = []
            
            for el in elements[:15]:
                if page.is_closed(): break
                try:
                    text = await el.inner_text(timeout=1000)
                    if not text or len(text.strip()) < 5:
                        continue
                        
                    is_hidden_ad = await el.evaluate("""node => {
                        const html = node.innerHTML.toLowerCase();
                        return node.querySelector('[data-text-ad], [data-matarget="ad"]') !== null || 
                               html.includes('sponsored') || 
                               html.includes('promoted') ||
                               html.includes('ad<');
                    }""")
                    
                    captured_data.append({"text": text.strip(), "is_ad": 1 if is_hidden_ad else 0})
                except Exception:
                    continue

            if captured_data:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                captured_texts_only = [] 
                
                for item in captured_data:
                    pk_id = f"feed_{p_name}_{plt_name}_{datetime.now().strftime('%H%M%S%f')}"
                    event_type = "TARGETED_AD" if item["is_ad"] else "ORGANIC_FEED_ITEM"
                    
                    if p_name in SESSION_METRICS:
                        if item["is_ad"]:
                            SESSION_METRICS[p_name]["ad_count"] += 1
                        else:
                            SESSION_METRICS[p_name]["organic_count"] += 1

                    safe_content = json.dumps({"text": item["text"]})

                    cursor.execute("""
                        INSERT OR IGNORE INTO Post (
                            pk_id, session_id, persona_name, platform, 
                            content_text, source_author, event_type, 
                            interaction_state, is_ad
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (pk_id, CURRENT_SESSION_ID, p_name, plt_name, safe_content, "Visual_Scrape", event_type, "VIEWED", item["is_ad"]))
                    
                    captured_texts_only.append(item["text"])
                    
                conn.commit()
                conn.close()
                
                self._save_to_platform_timeline(p_name, plt_name, "VISUAL_SCRAPE", captured_texts_only)
                log_telemetry(p_name, plt_name, "SCRAPE_SUCCESS", action="Visual_Audit")
                return captured_texts_only
            
            return []
            
        except Exception as e:
            if "closed" in str(e).lower():
                logger.debug(f"    [~] Scraper Context Closed Gracefully for {p_name}.")
            else:
                logger.debug(f"    [!] Scraper Error: {e}")
            return []

    def _save_to_platform_timeline(self, p_name, plt_name, event_type, data):
        folder = self._get_platform_folder(plt_name)
        data_dir = os.path.join(PROJECT_ROOT, "data", folder)
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, f"{folder}_Timeline.json")
        is_sso = "_sso" in p_name.lower()
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": CURRENT_SESSION_ID,
            "persona_name": p_name,
            "is_sso": is_sso,
            "event_type": event_type,
            "data": data
        }
        
        history = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f: history = json.load(f)
            except Exception: pass
                
        history.append(entry)
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(history, f, indent=4)

scraper_instance = Scraper()

async def scrape_feed_metadata(page, p_name, plt_name):
    return await scraper_instance.scrape_feed_metadata(page, p_name, plt_name)