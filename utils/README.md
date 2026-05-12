# 🧰 S.I.L.O. Utilities & Humanization (`utils/`)

This directory contains the core intelligence, state management, and biometric emulation engine for the S.I.L.O. framework. 

If the `navigation/` folder acts as the "muscles" executing clicks, the `utils/` folder acts as the **Brain and Nervous System**. It dictates how the bots physically interact with the browser to evade bot-detection, how they decide what content to consume, and how data is safely routed back to the SQLite database during high-concurrency multi-tab runs.

---

## 📂 File-by-File Architecture

Because the engine requires complex state management and biometric spoofing, the logic is split across several dedicated utility scripts:

### 1. `humanizer.py` (The Biometric Orchestrator)
This is the master interaction class. Instead of using standard Playwright clicks (which are instantly flagged by anti-bot systems like Cloudflare), all navigation files route their actions through the `Humanizer` object.
* **`human_scroll()`:** Applies large, randomized pixel jumps and yields to the DOM to simulate a real user spinning a mouse wheel, rather than linear bot scrolling.
* **`human_like_typing()`:** Instantly injects search queries into text boxes to bypass artificial typing lag while avoiding bot-mitigation triggers.
* **`simulate_reading_on_page()`:** Mimics a distracted human reading a webpage. It injects randomized pauses, scrolls up and down, and has a 70% chance of clicking random internal links to explore deeper into a site before returning to the main feed.
* **Central Logging:** Contains `log_click_to_db()` and `log_active_event_to_json()` to ensure every click is permanently recorded.

### 2. `video_handler.py` (The Engagement Brain)
This script mathematically decides if a bot should watch a video and whether it should leave a "Like".
* **The 5:1 Skip Ratio:** If a video does *not* match the persona's interests, the bot has an 83.3% chance of instantly scrolling past it. 
* **Attention Span:** If the bot stops on a video, it picks a randomized watch duration (10%, 25%, 50%, 75%, or 100% of the video length).

### 3. `post_interest.py` (The Persona Parser)
This script parses the `config/interests_wordlist.txt` file. 
* It understands persona-specific prefixes (e.g., `angela: skincare, luxury`).
* It exposes the `is_interested_in(text)` helper function, which all navigation and sniffer files use to rapidly test if an intercepted post aligns with the bot's predetermined filter bubble.

### 4. `feed_scraper.py` (The Visual Fallback)
If a network sniffer cannot find the hidden API payload for a website (or if the site uses encrypted GraphQL), the engine relies on this script.
* It uses the `DOM_MAP` in `registry.py` to visually rip the text of posts directly from the browser screen.
* It contains specific javascript evaluation logic to identify hidden "Sponsored" or "Ad" tags inside the HTML structure.

### 5. `shared_data.py` (The State Manager)
Maintains the live state of the simulation across all parallel tabs.
* Tracks the `SESSION_METRICS` (how many ads vs. organic posts have been seen).
* **`generate_dynamic_query()`:** Safely opens the `wordlist.txt` file and uses system-level entropy (`random.SystemRandom()`) to pick a non-repetitive search term for the bots to use.

### 6. `telemetry.py` (The Database Router)
Handles the `SessionLog` tracking. Because S.I.L.O. operates multiple active tabs simultaneously, standard database writes would cause "Database is Locked" errors. This script uses a secure context manager to safely insert logs into the SQLite database operating in WAL (Write-Ahead Logging) mode.

### 7. `google_utils.py` (The Ecosystem Helper)
Contains specialized logic for navigating the Google ecosystem:
* **`handle_google_consent()`:** Automatically detects and bypasses the European/Guest-mode "Accept All Cookies" popups and sign-in iframes that frequently block automated browsers.
* **`extract_google_text()`:** A regex cleaner that strips messy HTML and injected `<script>` tags out of raw web bodies to extract clean text for the Zero-Shot AI analyzer.

---

## 🧠 Customizing the Bot's Psychology

If you want to test how algorithms react to different *types* of users (e.g., a "hyper-engaged" user vs. a "passive" scroller), you can easily customize the engagement variables.

### Adjusting Attention Spans
Open `video_handler.py`. To make your bot watch *more* unrelated content (simulating a user who is easily distracted by clickbait), lower the skip ratio threshold:
```python
# Inside video_handler.py -> determine_video_engagement()
# Change 0.833 to a lower number (like 0.50) to make the bot watch MORE unrelated content
if random.random() < 0.833: 
    return False, 0.0, False, "None"
```

### Modifying Watch Durations
If a bot decides to watch non-interest content, it picks from this array. You can alter these numbers to simulate users with shorter or longer attention spans:
```python
# Simulating a user with zero attention span:
watch_percent = random.choice([0.05, 0.10, 0.15]) 
```

### Adjusting Reading Speed
Open `humanizer.py`. To make the bot read faster or slower, change the sleep bounds in the reading simulator:
```python
# Inside humanizer.py -> simulate_reading_on_page()
await asyncio.sleep(random.uniform(2, 4)) # Adjust these seconds to simulate faster/slower reading
```