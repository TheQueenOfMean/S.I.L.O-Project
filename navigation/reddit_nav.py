import random, asyncio, os, sys, sqlite3, time
from loguru import logger
from utils.video_handler import determine_video_engagement 
from utils.post_interest import load_interest_trigger_list, is_interested_in
from utils.shared_data import PERSONA_STATE
from utils.telemetry import log_telemetry

class RedditNav:
    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        if page.is_closed(): return
        platform = "Reddit"
        interests = load_interest_trigger_list(persona_name)
        
        if persona_name not in PERSONA_STATE: 
            PERSONA_STATE[persona_name] = {}
        PERSONA_STATE[persona_name]["current_query"] = query

        try:
            logger.info(f"    [🤖] Reddit: Starting Search Audit for '{query}'...")
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            search_box = "#header-search-bar, input[name='q'], shreddit-search-bar"
            if await page.is_visible(search_box, timeout=3000):
                await humanizer.human_like_typing(page, search_box, query)
                await page.keyboard.press("Enter")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except: pass

            if page.is_closed(): return
            await humanizer.human_scroll(persona_name, max_scrolls=2)
            await asyncio.sleep(1)

            if page.is_closed(): return
            posts = await page.locator("shreddit-post").all()
            if not posts:
                posts = await page.locator("div[data-testid='post-container']").all()

            random.shuffle(posts)
            for post in posts[:4]:
                if page.is_closed(): break
                try:
                    is_ad = await post.evaluate("node => node.hasAttribute('ad-id') || node.innerHTML.toLowerCase().includes('promoted')")
                    if is_ad: continue
                except: continue

                try:
                    title_loc = post.locator("a[slot='title'], h3").first
                    post_text = await title_loc.inner_text()
                except:
                    post_text = "Reddit Thread"

                is_interested, watch_percent, should_like, matched_trigger = await determine_video_engagement(persona_name, post_text, platform)

                if watch_percent == 0 and not is_interested:
                    continue

                if random.random() < 0.7:
                    try:
                        # FIX: Log opening the Reddit thread
                        await humanizer.log_click_to_db(persona_name, platform, post_text, event_type="POST_CLICK")
                        await title_loc.click(force=True, timeout=3000)
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=3000)
                        except: pass
                        
                        gallery_next = page.locator("button[aria-label='Next image'], shreddit-gallery button[aria-label='Next']").first
                        
                        if await gallery_next.is_visible(timeout=2000):
                            logger.info("    [🖼️] Reddit: Image gallery detected. Browsing photos...")
                            for _ in range(random.randint(1, 3)):
                                if page.is_closed(): break
                                try:
                                    await gallery_next.click(force=True, timeout=1000)
                                    await asyncio.sleep(random.uniform(1.5, 3.0))
                                except: break
                        else:
                            actual_read = random.uniform(5, 15) * watch_percent
                            logger.info(f"    [📖] Reddit: Reading text thread for {actual_read:.1f}s")
                            await asyncio.sleep(actual_read)
                            
                            if not page.is_closed():
                                await humanizer.human_scroll(persona_name, max_scrolls=1)

                        if should_like and not page.is_closed():
                            try:
                                upvote = page.locator("button[aria-label='upvote'], shreddit-aspect-ratio button").first
                                if await upvote.is_visible(timeout=1000):
                                    # FIX: Log the upvote click
                                    await humanizer.log_click_to_db(persona_name, platform, post_text, event_type="UPVOTE_CLICK")
                                    await upvote.click(force=True)
                                    logger.info("    [⬆️] Reddit: Upvoted post.")
                            except: pass

                        if not page.is_closed():
                            try:
                                await page.go_back(timeout=4000)
                            except: pass
                        await asyncio.sleep(0.5)
                        
                    except: pass
                else:
                    await asyncio.sleep(random.uniform(1, 3) * watch_percent)

            if not page.is_closed() and random.random() < 0.3:
                logger.info("    [🔍] Reddit: Checking sidebar/recent posts...")
                try:
                    recent_links = await page.locator("aside a[href*='/r/'], #right-sidebar-container a").all()
                    if recent_links:
                        target = random.choice(recent_links[:5])
                        await target.click(force=True, timeout=3000)
                        await asyncio.sleep(2)
                        await page.go_back(timeout=4000)
                except: pass

        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f" [!] Reddit Nav Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))