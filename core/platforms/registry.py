import asyncio
from sniffers.youtube_sniffer import intercept_youtube_feed
from sniffers.tiktok_sniffer import intercept_tiktok_feed
from sniffers.x_sniffer import intercept_x_feed
from sniffers.reddit_sniffer import intercept_reddit_feed
from sniffers.google_sniffer import sniff_google
from sniffers.yahoo_sniffer import sniff_yahoo

async def noop_login(page, email=None, password=None):
    """Real login is already handled manually via seeding. Do nothing."""
    await asyncio.sleep(0.1)

# --- 🎯 DOM MAP: 8 WEBSITES ---
# Crucial: 'feed_text' keys added for the Scraper to feed the AI Analysis
DOM_MAP = {
    "Google Search":  {
        "search_bar": "textarea[name='q'], input[name='q']", 
        "feed_text": "div.g, div[data-text-ad], div.uEierd, div#tvcap", 
        "result_link": "a[data-ved]"
    },
    "Google News":    {
        "search_bar": "input[aria-label='Search']", 
        "feed_text": "article h3", 
        "result_link": "a[href*='./articles/']"
    },
    "YouTube":        {
        "search_bar": "input#search", 
        "feed_text": "a#video-title-link, ytd-ad-slot-renderer", 
        "result_link": "a#video-title-link"
    },
    "Yahoo Search Feed": { 
        "search_bar": "input[name='p']", 
        "feed_text": "div.compTitle, li.searchCenterMiddle, li.ad, div.searchTopAds, div.dd.algo-ad", 
        "result_link": "a.ac-algo"
    },
    "Yahoo News":     {
        "search_bar": "input[name='p']", 
        "feed_text": "h3 a", 
        "result_link": "a.js-content-viewer, h3 a"
    },
    "TikTok":         {
        "search_bar": "input[type='search']", 
        "feed_text": "[data-e2e='browse-video-desc']", 
        "result_link": "a[href*='/video/']"
    },
    "X/Twitter":      {
        "search_bar": "input[data-testid='SearchBox_Search_Input']", 
        "feed_text": "[data-testid='tweetText']", 
        "result_link": "a[href*='/status/']"
    },
    "Reddit":         {
        "search_bar": "input[name='q']", 
        "feed_text": "shreddit-post a[slot='full-post-link']", 
        "result_link": "a[slot='full-post-link']"
    }
}

# --- 🚀 PLATFORMS: 8 WEBSITES ---
PLATFORMS = {
    "Google Search": {
        "url": "https://www.google.com", 
        "domains": ["google.com"], 
        "sniffer": sniff_google, 
        "login_func": noop_login
    },
    "Google News": {
        "url": "https://news.google.com", 
        "domains": ["news.google.com"], 
        "sniffer": sniff_google, 
        "login_func": noop_login
    },
    "YouTube": {
        "url": "https://www.youtube.com", 
        "domains": ["youtube.com", "youtu.be"], 
        "sniffer": intercept_youtube_feed, 
        "login_func": noop_login
    },
    "Yahoo Search Feed": {
        "url": "https://www.yahoo.com", # FIXED: Pointing to main domain to prevent blocking
        "domains": ["yahoo.com", "search.yahoo.com"], # FIXED: Ensuring base domain is captured
        "sniffer": sniff_yahoo, 
        "login_func": noop_login
    },
    "Yahoo News": {
        "url": "https://news.yahoo.com", 
        "domains": ["news.yahoo.com"], 
        "sniffer": sniff_yahoo, 
        "login_func": noop_login
    },
    "TikTok": {
        "url": "https://www.tiktok.com/foryou", 
        "domains": ["tiktok.com"], 
        "sniffer": intercept_tiktok_feed, 
        "login_func": noop_login
    },
    "X/Twitter": {
        "url": "https://x.com/home", 
        "domains": ["x.com", "twitter.com"], 
        "sniffer": intercept_x_feed, 
        "login_func": noop_login
    },
    "Reddit": {
        "url": "https://www.reddit.com", 
        "domains": ["reddit.com", "gql.reddit.com"], 
        "sniffer": intercept_reddit_feed, 
        "login_func": noop_login
    },
}