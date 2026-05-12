import asyncio
import random
import os
import sys
import sqlite3
import time
import datetime
import json
from loguru import logger
from core.database_manager import DB_PATH, CURRENT_SESSION_ID

# --- PATH INJECTOR ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Core Utils
from utils.shared_data import generate_dynamic_query, PERSONA_STATE
from utils.google_utils import handle_google_consent
from utils.feed_scraper import Scraper
from utils.telemetry import log_telemetry, log_session
from utils.post_interest import load_interest_trigger_list, is_interested_in

# THE BRAIN
from utils.video_handler import determine_video_engagement

# TOP-LEVEL NAV IMPORTS
from navigation.tiktok_nav import TikTokNav
from navigation.x_nav import XNav
from navigation.reddit_nav import RedditNav
from navigation.news_nav import NewsNav
from navigation.search_nav import SearchNav
from navigation.youtube_nav import YouTubeNav

class Humanizer:
    def __init__(self, page):
        self.page = page
        self.first_run = True
        self.scraper = Scraper() 

    async def log_active_event_to_json(self, persona_name, platform, event_type, data):
        """Logs session data to JSON for the S.I.L.O. audit."""
        try:
            platform_sub = platform.lower().replace(" ", "_")
            data_dir = os.path.join(PROJECT_ROOT, "data", platform_sub)
            os.makedirs(data_dir, exist_ok=True)
            file_path = os.path.join(data_dir, f"{persona_name}_Network.json")
            
            interests = load_interest_trigger_list(persona_name)
            content_str = str(data).lower()
            matched = next((w for w in interests if w in content_str), "None")
            data["interest_triggered"] = matched

            entry = {
                "timestamp": datetime.datetime.now().isoformat(), 
                "session": CURRENT_SESSION_ID, 
                "event": event_type, 
                "data": data
            }
            
            history = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except Exception: pass
            
            history.append(entry)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            logger.debug(f"JSON Bridge Error: {e}")

    async def log_click_to_db(self, persona_name, platform, content_text, event_type="CLICK_INTERACTION"):
        """Logs click events to the central SQLite database."""
        try:
            timestamp_ms = int(time.time() * 1000)
            safe_text = content_text[:500].replace('\n', ' ')
            
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Post (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f"click_{timestamp_ms}", CURRENT_SESSION_ID, persona_name, platform, 
                  json.dumps({"text": safe_text}), "Humanizer Interaction", event_type, "CLICKED", 0))
            conn.commit()
            conn.close()
            
            await self.log_active_event_to_json(persona_name, platform, "UI_CLICK", {"content": safe_text})
        except Exception as e:
            logger.error(f"    [!] Failed to log click: {e}")

    async def simulate_reading_on_page(self, persona_name):
        """Mimics human reading behavior with realistic pauses."""
        logger.info(f"    [📖] {persona_name}: Mimicking reading on external page...")
        try:
            if self.page.is_closed(): return
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception: pass
                
            await asyncio.sleep(random.uniform(2, 4))
            await self.human_scroll(persona_name, max_scrolls=4)
            
            if not self.page.is_closed() and random.random() < 0.7:  
                links_locator = self.page.locator("aside a, nav a, main a >> visible=true")
                link_count = await links_locator.count()
                
                if link_count > 0:
                    idx = random.randint(0, min(link_count - 1, 19))
                    target = links_locator.nth(idx)
                    
                    url = (await target.get_attribute("href")) or "Unknown"
                    logger.info(f"    [🔗] {persona_name}: Exploring inner link: {url[:50]}")
                    try:
                        await target.click(force=True, timeout=3000) # Fast click
                        try:
                            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except Exception: pass
                        
                        await self.log_active_event_to_json(persona_name, "External", "INTERNAL_READ_CLICK", {"url": url})
                        await asyncio.sleep(random.uniform(3, 7)) # Realistic reading pause
                        await self.human_scroll(persona_name, max_scrolls=3)
                        
                        if not self.page.is_closed():
                            try:
                                await self.page.go_back(wait_until="domcontentloaded", timeout=5000)
                            except Exception: pass
                    except Exception as e:
                        logger.debug(f"    [!] Failed to explore inner link: {e}")
        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.debug(f"    [!] Simulation interrupted: {e}")
        logger.info(f"    [🔙] {persona_name}: Finished reading.")

    async def perform_interaction(self, persona_name, platform_name, query=None):
        """Directs the bot to the appropriate platform navigation handler."""
        if self.first_run:
            logger.info(f"    [🤖] Humanizer Online: Steering {persona_name} on {platform_name}...")
            self.first_run = False

        if not query:
            query = generate_dynamic_query(persona_name, platform=platform_name.lower())

        log_session(persona_name, platform_name, "STAGE_START", action="Humanizer", target=query)

        try:
            if self.page.is_closed(): return
            await handle_google_consent(self.page, persona_name)
            
            if "Yahoo" in platform_name:
                await self.nuke_yahoo_overlays()

            if any(x in platform_name for x in ["Google Search", "Yahoo"]):
                await SearchNav.execute(self.page, self, persona_name, query)
            elif "News" in platform_name:
                await NewsNav.execute(self.page, self, persona_name, query)
            elif "YouTube" in platform_name:
                await YouTubeNav.execute(self.page, self, persona_name, query)
            elif "TikTok" in platform_name:
                await TikTokNav.execute(self.page, self, persona_name, query)
            elif "X Timeline" in platform_name or "Twitter" in platform_name:
                await XNav.execute(self.page, self, persona_name, query)
            elif "Reddit" in platform_name:
                await RedditNav.execute(self.page, self, persona_name, query)
            else:
                await self.human_scroll(persona_name)
        except Exception as e:
            if "closed" not in str(e).lower():
                logger.error(f"    [!] Humanizer Interaction Error: {e}")

    async def nuke_yahoo_overlays(self):
        selectors = ["button[name='agree']", ".da-overlay", "button:has-text('Maybe later')"]
        if self.page.is_closed(): return
        for s in selectors:
            try:
                if await self.page.is_visible(s, timeout=1000):
                    await self.page.click(s, force=True)
            except: pass

    async def human_scroll(self, persona_name=None, max_scrolls=5):
        """BLAZING FAST SCROLLING: Yields to DOM but does not pause artificially."""
        if self.page.is_closed(): return
        
        lower_bound = min(2, max_scrolls)
        upper_bound = max(2, max_scrolls)
        
        for _ in range(random.randint(lower_bound, upper_bound)):
            if self.page.is_closed(): break
            scroll_amt = random.randint(500, 1200) # Large pixel jumps
            try:
                await self.page.mouse.wheel(0, scroll_amt)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amt})")
                await asyncio.sleep(0.1) # Minimum yield to let browser render new content
            except: break

    async def human_like_typing(self, page, selector, text):
        """INSTANT TYPING: Injects the text entirely instead of letter-by-letter."""
        try:
            if page.is_closed(): return
            target = page.locator(selector).first
            await target.click(force=True, timeout=2000)
            logger.info(f"    [⌨️] Typing: '{text}'")
            
            # Instantly fill the input to bypass artificial typing lag
            await target.fill(text)
            await asyncio.sleep(0.2)
        except Exception as e:
            if "closed" not in str(e).lower():
                logger.error(f" [!] Typing failed for {selector}: {e}")

async def perform_interaction(page, persona_name, platform):
    bot = Humanizer(page)
    await bot.perform_interaction(persona_name, platform)