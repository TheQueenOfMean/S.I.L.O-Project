import random, asyncio, os, time, json
from loguru import logger
from utils.google_utils import handle_google_consent
from utils.shared_data import PERSONA_STATE
from utils.post_interest import is_interested_in
from utils.telemetry import log_telemetry

class SearchNav:
    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        if page.is_closed(): return
        url = page.url.lower()
        if "google.com" in url:
            await SearchNav._google_logic(page, humanizer, persona_name, query)
        elif "yahoo.com" in url:
            await SearchNav._yahoo_logic(page, humanizer, persona_name, query)

    @staticmethod
    async def _google_logic(page, humanizer, persona_name, query):
        platform = "Google Search"
        try:
            if page.is_closed(): return
            await handle_google_consent(page, persona_name)
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            input_sel = "textarea[name='q'], input[name='q']"
            if not page.is_closed() and await page.is_visible(input_sel, timeout=3000):
                await humanizer.human_like_typing(page, input_sel, query)
                await page.keyboard.press("Enter")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except: pass
                
            if page.is_closed(): return
            
            await humanizer.human_scroll(persona_name, max_scrolls=2)
            if page.is_closed(): return
            
            results = await page.locator("h3 >> visible=true").all()
            target = None
            
            for res in results[:6]:
                if page.is_closed(): break
                try:
                    text = await res.inner_text(timeout=1000)
                    if is_interested_in(text, persona_name):
                        target = res; break
                except: continue
            
            if not target and results and not page.is_closed(): 
                target = random.choice(results[:3])
            
            if target and not page.is_closed():
                target_text = await target.inner_text()
                logger.info(f"    [🔍] Google: Clicking result '{target_text[:30]}...'")
                # FIX: Added explicit event type
                await humanizer.log_click_to_db(persona_name, platform, target_text, event_type="SEARCH_CLICK")
                await target.evaluate("node => node.removeAttribute('target')")
                
                try:
                    await target.click(force=True, timeout=3000)
                except: pass
                    
                if not page.is_closed():
                    await humanizer.simulate_reading_on_page(persona_name)
                
                if not page.is_closed():
                    try:
                        await page.go_back(timeout=4000)
                    except: pass
                    
        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"Google Search Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))

    @staticmethod
    async def _yahoo_logic(page, humanizer, persona_name, query):
        platform = "Yahoo Search"
        try:
            if page.is_closed(): return
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            input_sel = "input#yschsp, input#ybar-sbq, input[name='p']"
            if not page.is_closed() and await page.is_visible(input_sel, timeout=3000):
                await humanizer.human_like_typing(page, input_sel, query)
                await page.keyboard.press("Enter")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except: pass
            
            if page.is_closed(): return
            await humanizer.human_scroll(persona_name, max_scrolls=2)

            if not page.is_closed():
                await page.evaluate("""() => {
                    const terms = ['scout', 'ai assistant'];
                    document.querySelectorAll('*').forEach(el => {
                        const classStr = (typeof el.className === 'string') ? el.className : (el.className.baseVal || "");
                        const idStr = el.id || "";
                        const content = (el.innerText || classStr || idStr || "").toLowerCase();
                        if (terms.some(t => content.includes(t))) { el.remove(); }
                    });
                }""")
            
            if page.is_closed(): return
            results = await page.locator("h3.title a, .compTitle a, a.d-ib >> visible=true").all()
            target = None
            
            for res in results[:6]:
                if page.is_closed(): break
                try:
                    href = (await res.get_attribute("href")) or ""
                    title_text = (await res.inner_text(timeout=1000)).lower()
                    if "scout" in href.lower() or "scout" in title_text: continue
                    if is_interested_in(title_text, persona_name):
                        target = res; break
                except: continue
            
            # FIX: Added the missing fallback so Yahoo actually clicks results
            if not target and results and not page.is_closed(): 
                target = random.choice(results[:3])
            
            if target and not page.is_closed():
                target_text = await target.inner_text()
                logger.info(f"    [🔍] Yahoo: Clicking result '{target_text[:30]}...'")
                # FIX: Logging the click to the DB
                await humanizer.log_click_to_db(persona_name, platform, target_text, event_type="SEARCH_CLICK")
                await target.evaluate("node => node.removeAttribute('target')")
                
                try:
                    await target.click(force=True, timeout=3000)
                except: pass
                    
                if not page.is_closed():
                    await humanizer.simulate_reading_on_page(persona_name)
                
                if not page.is_closed():
                    try:
                        await page.go_back(timeout=4000)
                    except: pass
                    
        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"Yahoo Search Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))