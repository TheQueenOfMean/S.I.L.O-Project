import random, asyncio, os, time
from loguru import logger
from utils.google_utils import handle_google_consent
from utils.shared_data import PERSONA_STATE
from utils.post_interest import is_interested_in
from utils.telemetry import log_telemetry

class NewsNav:
    @staticmethod
    async def execute(page, humanizer, persona_name, query): 
        if page.is_closed(): return
        if persona_name not in PERSONA_STATE: 
            PERSONA_STATE[persona_name] = {}
        if "news_searches" not in PERSONA_STATE[persona_name]:
            PERSONA_STATE[persona_name]["news_searches"] = 0

        url = page.url.lower()
        if "google.com" in url:
            await NewsNav._google_news_logic(page, humanizer, persona_name, query)
        elif "yahoo.com" in url:
            await NewsNav._yahoo_news_logic(page, humanizer, persona_name, query)

    @staticmethod
    async def _google_news_logic(page, humanizer, persona_name, query):
        platform = "Google News"
        try:
            if page.is_closed(): return
            await handle_google_consent(page, persona_name)
            
            for _ in range(3):
                if page.is_closed(): return
                await page.keyboard.press("PageDown")
                await asyncio.sleep(0.1)
            
            await humanizer.human_scroll(persona_name, max_scrolls=2)
            
            if page.is_closed(): return
            articles = await page.locator("a[href*='./articles/'] >> visible=true").all()
            
            target = None
            for art in articles[:10]:
                if page.is_closed(): break
                try:
                    if is_interested_in(await art.inner_text(timeout=500), persona_name):
                        target = art; break
                except: continue
            
            if not target and articles and not page.is_closed(): 
                target = random.choice(articles[:3])
            
            if target and not page.is_closed():
                target_text = await target.inner_text()
                logger.info(f"    [📰] Google News: Clicking article '{target_text[:30]}...'")
                # FIX: Explicit event type
                await humanizer.log_click_to_db(persona_name, platform, target_text, event_type="NEWS_CLICK")
                
                try:
                    await target.click(force=True, timeout=2000)
                except: pass
                
                if not page.is_closed():
                    await humanizer.simulate_reading_on_page(persona_name)
                
                if not page.is_closed():
                    try:
                        await page.go_back(timeout=3000)
                    except:
                        await page.goto("https://news.google.com", wait_until="domcontentloaded")

            if PERSONA_STATE[persona_name]["news_searches"] < 2 and not page.is_closed():
                search_input = "input[aria-label*='Search'], input[role='combobox']"
                if await page.is_visible(search_input, timeout=1000):
                    await humanizer.human_like_typing(page, search_input, query)
                    await page.keyboard.press("Enter")
                    PERSONA_STATE[persona_name]["news_searches"] += 1
                    
        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"Google News Error: {e}")

    @staticmethod
    async def _yahoo_news_logic(page, humanizer, persona_name, query):
        platform = "Yahoo News"
        try:
            if page.is_closed(): return
            
            for _ in range(3):
                if page.is_closed(): return
                await page.keyboard.press("PageDown")
                await asyncio.sleep(0.1)

            await humanizer.human_scroll(persona_name, max_scrolls=2)
            
            if not page.is_closed():
                await page.evaluate("""() => {
                    const terms = ['scout', 'ai assistant', 'search.yahoo.com'];
                    document.querySelectorAll('*').forEach(el => {
                        const classStr = (typeof el.className === 'string') ? el.className : (el.className.baseVal || "");
                        const href = el.href ? el.href.toLowerCase() : '';
                        const content = (el.innerText || classStr || el.id || '').toLowerCase();
                        if (terms.some(t => content.includes(t) || href.includes(t))) { el.remove(); }
                    });
                }""")

            if page.is_closed(): return
            articles = await page.locator("#Col1-0-Stream a >> visible=true, article a >> visible=true").all()
            target = None
            
            for art in articles[:8]:
                if page.is_closed(): break
                try:
                    if is_interested_in(await art.inner_text(timeout=500), persona_name):
                        target = art; break
                except: continue
            
            # FIX: Added the missing fallback so Yahoo News actually clicks articles
            if not target and articles and not page.is_closed(): 
                target = random.choice(articles[:3])
            
            if target and not page.is_closed():
                target_text = await target.inner_text()
                logger.info(f"    [📰] Yahoo News: Clicking article '{target_text[:30]}...'")
                # FIX: Logging the click to the DB
                await humanizer.log_click_to_db(persona_name, platform, target_text, event_type="NEWS_CLICK")
                
                try:
                    await target.click(force=True, timeout=2000)
                except: pass
                
                if not page.is_closed():
                    await humanizer.simulate_reading_on_page(persona_name)
                
                if not page.is_closed():
                    try:
                        await page.go_back(timeout=3000)
                    except:
                        await page.goto("https://news.yahoo.com", wait_until="domcontentloaded")

            if PERSONA_STATE[persona_name]["news_searches"] < 2 and not page.is_closed():
                input_sel = "input#ybar-sbq, [name='p']"
                if await page.is_visible(input_sel, timeout=1000):
                    await humanizer.human_like_typing(page, input_sel, query)
                    await page.keyboard.press("Enter")
                    PERSONA_STATE[persona_name]["news_searches"] += 1
                    
        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"Yahoo News Error: {e}")