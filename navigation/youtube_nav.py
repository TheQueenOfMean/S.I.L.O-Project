import random
import asyncio
import time
from loguru import logger

from utils.video_handler import determine_video_engagement
from utils.google_utils import handle_google_consent
from utils.shared_data import PERSONA_STATE, generate_dynamic_query
from utils.telemetry import log_telemetry

class YouTubeNav:
    @staticmethod
    async def skip_youtube_ads(page, persona_name):
        ad_selectors = [
            ".ytp-ad-skip-button", ".ytp-ad-skip-button-modern", 
            ".ytp-skip-ad-button", "button.ytp-ad-skip-button-container",
            "[id^='skip-button'] button", ".videoAdUiSkipButton"
        ]
        if page.is_closed(): return False
        try:
            for sel in ad_selectors:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=200):
                    await btn.evaluate("node => node.click()")
                    logger.info(f"    [⏩] {persona_name}: YouTube Ad Skipped.")
                    return True
            
            overlay_close = page.locator(".ytp-ad-overlay-close-button").first
            if await overlay_close.is_visible(timeout=200):
                await overlay_close.evaluate("node => node.click()")
        except Exception: pass
        return False

    @staticmethod
    async def click_youtube_like(page):
        if page.is_closed(): return
        try:
            btn = page.locator("like-button-view-model button, #segmented-like-button button").locator("visible=true").first
            await btn.click(force=True, timeout=1000)
            logger.info("    [❤️] YouTube: Liked video.")
        except: pass

    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        platform = "YouTube"
        term = query if query else generate_dynamic_query(persona_name, platform)
        if page.is_closed(): return
        
        try:
            logger.info(f"    [🎥] YouTube: Starting Search for '{term}'...")
            await handle_google_consent(page, persona_name)
            log_telemetry(persona_name, platform, "SEARCH_START", target=term)
            
            search_input = "input#search, input[name='search_query']"
            if await page.is_visible(search_input, timeout=3000):
                await humanizer.human_like_typing(page, search_input, term)
                await page.keyboard.press("Enter")
                
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except: pass

            if page.is_closed(): return
            await humanizer.human_scroll(persona_name, max_scrolls=2)
            await asyncio.sleep(1)

            if page.is_closed(): return
            video_items = await page.locator("ytd-video-renderer #video-title, ytd-reel-item-renderer #video-title").locator("visible=true").all()
            
            if not video_items:
                await humanizer.human_scroll(persona_name, max_scrolls=2)
                video_items = await page.locator("ytd-video-renderer #video-title, ytd-reel-item-renderer #video-title").locator("visible=true").all()

            random.shuffle(video_items)
            target_found = False
            
            for item in video_items[:10]:
                if page.is_closed(): break
                try:
                    title_text = await item.inner_text()
                except:
                    title_text = "YouTube Video Content"

                is_interested, watch_percent, should_like, trigger = await determine_video_engagement(persona_name, title_text, platform)

                if watch_percent == 0 and not is_interested:
                    continue

                logger.info(f"    [▶️] YouTube: Opening '{title_text[:40]}...' (Watch: {int(watch_percent*100)}%)")
                try:
                    # FIX: Explicitly log the video click to the database
                    await humanizer.log_click_to_db(persona_name, platform, title_text, event_type="VIDEO_CLICK")
                    await item.click(force=True, timeout=3000)
                except: continue
                
                target_found = True
                await asyncio.sleep(2)
                
                max_watch = 60 if "short" in title_text.lower() or "shorts" in page.url else 120
                watch_time = max_watch * watch_percent
                start_watch = time.time()
                
                logger.info(f"    [👀] YouTube: Commencing {watch_time:.1f}s watch.")
                while (time.time() - start_watch) < watch_time:
                    if page.is_closed(): break
                    if await YouTubeNav.skip_youtube_ads(page, persona_name):
                        start_watch += 5
                    await asyncio.sleep(1) 

                if not page.is_closed():
                    if should_like:
                        await YouTubeNav.click_youtube_like(page)

                    if is_interested and "_sso" in persona_name.lower():
                        try:
                            sub_btn = page.locator("#subscribe-button button").first
                            if await sub_btn.is_visible(timeout=1000):
                                await sub_btn.click(force=True)
                        except: pass

                    try:
                        await page.go_back(timeout=4000)
                    except: pass
                    await asyncio.sleep(1)
                break 

            if not target_found and not page.is_closed():
                await humanizer.human_scroll(persona_name, max_scrolls=2)

        except Exception as e:
            if "closed" not in str(e).lower():
                logger.error(f"    [!] YouTube Nav Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))