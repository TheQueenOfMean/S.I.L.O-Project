import random, asyncio, os, sys, time, sqlite3
from loguru import logger
from utils.video_handler import determine_video_engagement
from utils.shared_data import PERSONA_STATE
from utils.telemetry import log_telemetry
from utils.post_interest import load_interest_trigger_list

class TikTokNav:
    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        if page.is_closed(): return
        platform = "TikTok FYP"
        if persona_name not in PERSONA_STATE: PERSONA_STATE[persona_name] = {}
        PERSONA_STATE[persona_name]["current_query"] = query

        try:
            logger.info(f"    [🎬] TikTok: Starting Search Audit for '{query}'...")
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            search_url = f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}"
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            except: pass
            
            if page.is_closed(): return
            await asyncio.sleep(1)
            
            if "shop" in page.url.lower():
                video_tab = page.locator("div[role='tab']:has-text('Videos')").first
                if await video_tab.is_visible(timeout=2000):
                    await video_tab.click(force=True)
                    await asyncio.sleep(1)

            if page.is_closed(): return
            await humanizer.human_scroll(persona_name, max_scrolls=2)

            video_items = await page.locator("div[data-e2e='search_video-item']").all()
            if not video_items: return

            random.shuffle(video_items)
            target_video = None
            title_text = "TikTok Content"
            
            for item in video_items[:8]:
                if page.is_closed(): break
                try:
                    title_text = await item.inner_text()
                    is_int, watch, like, trig = await determine_video_engagement(persona_name, title_text, platform)
                    if watch > 0: 
                        target_video = item
                        break
                except: continue

            if not target_video and video_items and not page.is_closed():
                target_video = video_items[0]

            if target_video and not page.is_closed():
                try:
                    # FIX: Explicitly log the video click to the database
                    await humanizer.log_click_to_db(persona_name, platform, title_text, event_type="VIDEO_CLICK")
                    await target_video.click(force=True, timeout=3000)
                except: return
                await asyncio.sleep(2)
            else:
                return 

            for i in range(random.randint(3, 5)):
                if page.is_closed(): break
                try:
                    title_loc = page.locator("div[data-e2e='browse-video-desc'], h1").first
                    title_text = await title_loc.inner_text() if await title_loc.is_visible(timeout=1000) else "TikTok Content"
                except:
                    title_text = "TikTok Content"

                is_interested, watch_percent, should_like, trigger = await determine_video_engagement(persona_name, title_text, platform)
                
                if watch_percent > 0:
                    actual_duration = 20 * watch_percent
                    logger.info(f"    [👀] TikTok: Watching {int(watch_percent*100)}% ({actual_duration:.1f}s)")
                    await asyncio.sleep(actual_duration)
                    
                    if should_like and not page.is_closed():
                        try:
                            like_btn = page.locator("span[data-e2e='browse-like-icon']").first
                            # FIX: Log the like interaction
                            await humanizer.log_click_to_db(persona_name, platform, title_text, event_type="LIKE_CLICK")
                            await like_btn.click(force=True, timeout=1000)
                        except: pass
                
                if is_interested and not page.is_closed():
                    try:
                        follow_btn = page.locator("button[data-e2e='feed-follow'], [aria-label='Follow']").first
                        if await follow_btn.is_visible(timeout=1000):
                            await follow_btn.click(force=True)
                    except: pass
                
                if not page.is_closed():
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.5)

        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"TikTok Nav Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))