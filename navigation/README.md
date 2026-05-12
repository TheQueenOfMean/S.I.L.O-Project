# 🗺️ S.I.L.O. Navigation Modules (`navigation/`)

This directory houses the site-specific interaction scripts used by the S.I.L.O. framework. While the `humanizer.py` file acts as the "brain" that manages the overall browsing session, these navigation files act as the "muscles," executing the precise scrolling, clicking, and reading behaviors required for each unique platform.

Because every website has a different DOM structure (CSS selectors, pop-ups, infinite scrolls), abstracting the navigation logic into individual files keeps the framework modular and prevents the core engine from becoming bloated.

---

## 🏗️ How the Navigation System Works

When the Stealth Orchestrator focuses on a specific tab, the `humanizer.py` script identifies the platform and routes the execution flow to the corresponding navigation class in this folder. 

For example, if the active tab is `X/Twitter`, the humanizer calls `XNav.execute(...)`. The `XNav` class then takes over the Playwright `page` object, handles X-specific modals, scrolls the timeline, reads tweets, and triggers the S.I.L.O. video engagement algorithm to determine if it should "Like" or "Follow."

---

## 🛠️ Creating Custom Navigation Files

If you add a new target website to `registry.py`, you must also create a custom navigation file here to teach the Humanizer how to organically browse that specific site. 

### Step 1: Create the Boilerplate Class
Create a new Python file (e.g., `instagram_nav.py`) in this directory. Every navigation class must contain an asynchronous `execute()` static method that accepts the Playwright page, the humanizer instance, the persona name, and the current search query.

```python
import random, asyncio
from loguru import logger
from utils.telemetry import log_telemetry

class CustomNav:
    @staticmethod
    async def execute(page, humanizer, persona_name, query):
        # 1. Always check if the page was closed during tab-switching
        if page.is_closed(): return
        
        platform = "Your Custom Platform"
        
        try:
            logger.info(f"    [🧭] CustomNav: Starting Audit for {persona_name}...")
            log_telemetry(persona_name, platform, "AUDIT_START", target=query)
            
            # 2. Add your custom DOM interaction logic here
            await humanizer.human_scroll(persona_name, max_scrolls=3)
            
        except Exception as e:
            if "closed" not in str(e).lower():
                logger.error(f"    [!] Custom Nav Error: {e}")
                log_telemetry(persona_name, platform, "NAV_ERROR", target=str(e))
```

### Step 2: Implement Human-Like Interactions
Instead of writing raw Playwright commands (which often look like bots), use the built-in methods passed through the `humanizer` object to simulate human biometrics:

* **Scrolling:** `await humanizer.human_scroll(persona_name, max_scrolls=2)`
* **Typing:** `await humanizer.human_like_typing(page, "input.search", query)`
* **Reading:** `await humanizer.simulate_reading_on_page(persona_name)`

### Step 3: Log Engagement to the Database
To measure recommendation drift, you must log the bot's clicks and interactions back to the SQLite database. Whenever your custom navigation script clicks a post or an article, use the built-in logging method:

```python
# Example: Logging a click on a news article
await humanizer.log_click_to_db(
    persona_name=persona_name, 
    platform=platform, 
    content_text=target_article_text, 
    event_type="ARTICLE_CLICK"
)
```

### Step 4: Route the Humanizer to Your New File
Once your custom navigation file is built, open `utils/humanizer.py`. Import your new class at the top of the file, and add it to the routing logic inside the `perform_interaction()` method:

```python
# Inside humanizer.py -> perform_interaction()
elif "Your Custom Platform" in platform_name:
    await CustomNav.execute(self.page, self, persona_name, query)
```