import os
import sys
import asyncio
import time
import random 
from loguru import logger

# --- ⚙️ SYSTEM PATHING ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- 📁 REGISTRY & CORE IMPORTS ---
from core.platforms.registry import PLATFORMS, DOM_MAP
from core.database_manager import DB_PATH, CURRENT_SESSION_ID
from core.stealth_launcher import StealthLauncher 

# --- 🧪 UTILITY & TELEMETRY IMPORTS ---
from utils.humanizer import perform_interaction
from utils.telemetry import log_telemetry, BASE_DIR
from utils.shared_data import SESSION_METRICS, PERSONA_STATE
from utils.feed_scraper import Scraper # <-- FIXED: Importing the Class

async def run_persona_session(persona, minutes=30, headless=True):
    persona_name = persona['name']
    session_path = persona['path']
    mode_text = "HEADLESS" if headless else "VISIBLE"
    logger.info(f" [🚀] STARTING STEALTH ENGINE ({mode_text}): {persona_name} (MULTI-TAB MODE)")
    
    context, playwright_lib = await StealthLauncher.launch_persona_context(
        profile_dir=session_path, 
        headless=headless
    )

    try:
        pages = {}
        for platform_name, config in PLATFORMS.items():
            logger.info(f" [🆕] Opening new tab for {platform_name}...")
            page = await context.new_page()
            page.on("response", lambda res: asyncio.create_task(route_to_sniffers(res, persona_name)))
            
            try:
                await page.goto(config['url'], wait_until="domcontentloaded", timeout=60000)
                pages[platform_name] = page
            except Exception as e:
                logger.warning(f" [!] Failed to load {platform_name} on startup: {e}")

        if not pages:
            logger.error(f" [❌] No platforms loaded successfully for {persona_name}. Aborting.")
            return

        end_time = time.time() + (minutes * 60)
        platform_names = list(pages.keys())

        while time.time() < end_time:
            active_platform = random.choice(platform_names)
            active_page = pages[active_platform]
            
            human_attention_span = random.randint(60, 600)
            tab_end_time = time.time() + human_attention_span
            
            logger.info(f" [🔄] Switching focus to {active_platform}. Actively browsing for {human_attention_span // 60}m {human_attention_span % 60}s...")
            
            try:
                await active_page.bring_to_front()
                
                while time.time() < tab_end_time and time.time() < end_time:
                    # --- FIXED: Instantiate Scraper Object ---
                    scraper = Scraper()
                    await scraper.scrape_feed_metadata(active_page, persona_name, active_platform)
                    
                    await perform_interaction(active_page, persona_name, active_platform)
                    log_telemetry(persona_name, active_platform, "SUCCESS", action="Active_Browsing")
                    await asyncio.sleep(random.randint(5, 15))
                    
            except Exception as e:
                logger.warning(f" [!] Error while interacting with {active_platform}: {e}")
                
    finally:
        await StealthLauncher.close_all(context, playwright_lib)

async def route_to_sniffers(response, persona_name):
    url = response.url.lower()
    try:
        for platform_name, config in PLATFORMS.items():
            domains = config.get("domains", [])
            if any(domain in url for domain in domains):
                sniffer_function = config.get("sniffer")
                if sniffer_function:
                    await sniffer_function(response, persona_name)
                    return 
    except Exception as e:
        logger.debug(f"Sniffer Routing Error on {url}: {e}")