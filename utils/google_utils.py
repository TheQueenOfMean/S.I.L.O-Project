import re
import asyncio
from loguru import logger

def extract_google_text(raw_body):
    """Strips HTML/JS to extract readable text for the audit."""
    try:
        clean_text = re.sub(r'<(script|style).*?>.*?</\1>', '', raw_body, flags=re.DOTALL)
        clean_text = re.sub(r'<.*?>', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text[:5000]
    except Exception as e:
        logger.error(f"Error cleaning Google data: {e}")
        return raw_body[:1000]

async def handle_google_consent(page, persona_name):
    """Handles mandatory cookie pop-ups for logged-out/Guest users."""
    try:
        consent_buttons = [
            "button:has-text('Accept all')", 
            "button:has-text('I agree')", 
            "#L2AGLb", 
            "button[aria-label='Accept all']"
        ]
        
        for selector in consent_buttons:
            if await page.is_visible(selector, timeout=2500):
                await page.click(selector)
                logger.info(f"    [🍪] {persona_name}: Google Consent Accepted.")
                await asyncio.sleep(2) 
                break
                
        # Close 'Sign in with Google' guest iframe prompts
        iframe = page.frame_locator("iframe[title*='Sign in with Google']").first
        if await iframe.locator("button[aria-label='Close']").is_visible(timeout=1000):
            await iframe.locator("button[aria-label='Close']").click()
    except Exception: pass