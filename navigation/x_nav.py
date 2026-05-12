import asyncio
import os
import sys
import random
import sqlite3
import time
from loguru import logger
from utils.video_handler import determine_video_engagement 
from utils.post_interest import load_interest_trigger_list, is_interested_in
from utils.shared_data import PERSONA_STATE
from utils.telemetry import log_telemetry

class XNav:
    @staticmethod
    async def nuke_x_modals(page):
        if page.is_closed(): return
        modals = [
            "button[aria-label='Close']", 
            "div[data-testid='app-bar-close']",
            "div[role='button']:has-text('Not now')"
        ]
        for selector in modals:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True)
            except: pass

    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        if page.is_closed(): return
        platform = "X Timeline"
        interests = load_interest_trigger_list(persona_name)
        
        if persona_name not in PERSONA_STATE: PERSONA_STATE[persona_name] = {}
        PERSONA_STATE[persona_name]["current_query"] = query

        try:
            logger.info(f"    [🐦] X: Starting Audit for {persona_name}...")
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except: pass
            
            await XNav.nuke_x_modals(page)

            if not page.is_closed() and random.random() < 0.2:
                trends = await page.locator("div[data-testid='trend'], [data-testid='sidebarColumn'] a").all()
                if trends:
                    target_trend = random.choice(trends[:5])
                    try:
                        trend_text = await target_trend.inner_text()
                        if is_interested_in(trend_text, persona_name):
                            # FIX: Log the trend click
                            await humanizer.log_click_to_db(persona_name, platform, trend_text, event_type="TREND_CLICK")
                            await target_trend.click(force=True, timeout=2000)
                            await asyncio.sleep(2)
                            await XNav.nuke_x_modals(page)
                    except: pass

            for cycle in range(random.randint(2, 4)):
                if page.is_closed(): return
                await XNav.nuke_x_modals(page)
                
                await humanizer.human_scroll(persona_name, max_scrolls=2)
                await asyncio.sleep(0.5)

                if page.is_closed(): return
                tweets = await page.locator("article[data-testid='tweet'] >> visible=true").all()
                if not tweets: continue

                random.shuffle(tweets)
                for tweet in tweets[:3]:
                    if page.is_closed(): break
                    try:
                        tweet_text = await tweet.locator("div[data-testid='tweetText']").first.inner_text(timeout=1000)
                    except:
                        tweet_text = "X Content"

                    is_interested, watch_percent, should_like, trigger = await determine_video_engagement(persona_name, tweet_text, platform)

                    if watch_percent == 0 and not is_interested: continue

                    actual_read = random.uniform(5, 12) * watch_percent
                    logger.info(f"    [📖] X: Reading Tweet for {actual_read:.1f}s")
                    await asyncio.sleep(actual_read)

                    if should_like and not page.is_closed():
                        try:
                            like_btn = tweet.locator("button[data-testid='like']").first
                            # FIX: Log the Like
                            await humanizer.log_click_to_db(persona_name, platform, tweet_text, event_type="LIKE_CLICK")
                            await like_btn.click(force=True, timeout=1000)
                        except: pass

                    if is_interested and not page.is_closed():
                        try:
                            follow_btn = tweet.locator("button:has-text('Follow')").first
                            if await follow_btn.is_visible(timeout=1000):
                                # FIX: Log the Follow
                                await humanizer.log_click_to_db(persona_name, platform, tweet_text, event_type="FOLLOW_CLICK")
                                await follow_btn.click(force=True)
                        except: pass

                    if not page.is_closed() and await tweet.locator("div[data-testid='videoComponent'], video").count() > 0:
                        actual_watch = 15 * watch_percent
                        logger.info(f"    [📺] X: Watching Video for {actual_watch:.1f}s")
                        await asyncio.sleep(actual_watch)

            await XNav.nuke_x_modals(page)

        except Exception as e: 
            if "closed" not in str(e).lower():
                logger.error(f"    [!] X Nav Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))