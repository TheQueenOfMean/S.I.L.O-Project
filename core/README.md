# ⚙️ S.I.L.O. Core Infrastructure (`core/`)

This directory contains the central nervous system and foundational infrastructure of the S.I.L.O. framework. 

While the `utils/` and `navigation/` folders dictate *how* the bot behaves on specific websites, the `core/` files handle the heavy lifting: physically launching the stealth browsers, managing the parallel multi-tab event loops, and ensuring high-volume telemetry data is safely written to the database without locking errors.

---

## 📂 File-by-File Architecture

### 1. `engine.py` (The Master Orchestrator)
This is the main event loop for the simulation. When `sequential_orchestrator.py` initiates a run, it calls `run_persona_session()` inside this file.
* **Multi-Tab Management:** It dynamically reads `registry.py` and opens a parallel background tab for every single Target Domain. 
* **Focus Shifting (Attention Span):** It randomly selects an active tab and brings it to the front for a random duration (between 1 and 10 minutes) before switching to another tab. This simulates a real human bouncing between YouTube, Reddit, and News sites.
* **Traffic Routing:** It attaches a network listener (`route_to_sniffers`) to every tab, feeding raw JSON payloads directly into the passive sniffers before they even render.

### 2. `stealth_launcher.py` (The Anti-Bot Bypass)
This script handles the physical instantiation of the Chromium browser using **Patchright** (a stealth-focused fork of Playwright).
* **Strict Versioning:** It explicitly syncs the Chromium executable path with the exact version used during the `seed_master.py` phase. This prevents "downgrade crashes" and avoids triggering fingerprinting alarms.
* **Persistent Contexts:** It bypasses logins by loading the physical `user_data_dir` (the browser cache containing cookies and LocalStorage) generated during the seeding phase.
* **Chromium Flags:** It injects specialized arguments (e.g., `--disable-blink-features=AutomationControlled`) to strip away the standard metadata that flags headless browsers to bot-mitigation systems like Cloudflare.

### 3. `database_manager.py` (The Telemetry Hub)
Because S.I.L.O. operates 8+ active tabs simultaneously, standard SQLite would instantly crash with "Database is Locked" errors. This file solves that concurrency issue.
* **WAL Mode:** It permanently configures the SQLite database (`silo_audit.db`) to use Write-Ahead Logging (`PRAGMA journal_mode=WAL`). This allows simultaneous, multi-threaded writes from the various sniffers and humanizer scripts.
* **Schema Definition:** It initializes the relational tables (`Post`, `SessionLog`, `Interpretation`) that bridge the raw data collection phase with the Zero-Shot AI analytics pipeline.

---

## 🛠️ Customizing & Scaling the Core Engine

If you want to fundamentally alter how the framework operates or scale your experimental cohorts, you can tune the parameters that interact with these core files.

### 1. Visualizing the Bots (Headed vs. Headless Mode)
To conserve local CPU and RAM, the master orchestrator runs the S.I.L.O. simulation in **Headless mode** by default (the browser operates invisibly in the background). 

However, if you want to visually monitor the Custom Humanizer scrolling, typing, and navigating the websites in real-time, you can toggle the engine to "Headed" mode. Open `sequential_orchestrator.py` and change the `headless` parameter to `False` in the execution loops:
```python
# Inside sequential_orchestrator.py
await run_persona_session(ANGELA, minutes=30, headless=False) # Changed to False to make browser visible
```

### 2. Scaling the Simulation (Adding More Personas)
The core engine is built to handle as many personas as your hardware supports. If you added new personas to your seeding configuration, you must tell the main orchestrator to run them.
Open the root `sequential_orchestrator.py` file and define your new personas, then add them to the execution queue:

```python
# Define your newly seeded personas
ANGELA = {"name": "Angela_SSO", "path": "sessions/angela_sso_v2", "sso": True}
DAVID = {"name": "David_SSO", "path": "sessions/david_sso", "sso": True}
MICHELLE = {"name": "Michelle_Unique", "path": "sessions/michelle_unique_v2", "sso": False}

async def execute_simulation(mode):
    # Pass them into the core engine loop
    await run_persona_session(ANGELA, minutes=30, headless=True) 
    gc.collect(); await asyncio.sleep(10) # Always flush RAM between runs
    
    await run_persona_session(DAVID, minutes=30, headless=True) 
    gc.collect(); await asyncio.sleep(10)
    
    await run_persona_session(MICHELLE, minutes=30, headless=True)
```

### 3. Integrating Custom Websites & SSO Providers
You **do not** need to rewrite any logic inside `engine.py` to test new websites or different SSO providers (like Microsoft or Apple). 
* **Dynamic Import:** The `engine.py` loop dynamically imports the `PLATFORMS` dictionary from `core/platforms/registry.py`. 
* **Automatic Scaling:** If you register a new website in the registry and seed an SSO account for it, the core engine will automatically open a new parallel tab for it, route its traffic to your sniffers, and integrate it into the humanizer's randomized focus-shifting loop without any additional core modifications.

### 4. Adjusting the Tab Switching Speed (User Focus)
By default, the engine simulates a user who stays on a single website for 1 to 10 minutes before getting distracted and switching tabs. To simulate a "doom-scroller" with a very short attention span, lower these bounds:
```python
# Inside engine.py -> run_persona_session()
# Change to stay on a tab for only 30 to 90 seconds
human_attention_span = random.randint(30, 90) 
tab_end_time = time.time() + human_attention_span
```

### 5. Injecting Proxies or Custom Browser Flags
If you are running S.I.L.O. on a machine that requires a proxy, or if you want to disable images to save RAM when scaling to 10+ target websites, add native Chromium flags to the launcher:
```python
# Inside stealth_launcher.py -> launch_persona_context()
args = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--password-store=basic",
    "--start-maximized",
    # Add custom flags here:
    "--proxy-server=http://your-proxy-ip:port", 
    "--blink-settings=imagesEnabled=false" # Disables image rendering to save RAM
]
```

### 6. Database Timeout Tuning
If you scale the experiment up to 20+ target websites or multiple concurrent personas, the SQLite database will experience extreme I/O pressure. If you see locking errors in your console, increase the timeout limits:
```python
# Inside database_manager.py -> get_db_connection()
# Increase the timeout from 30.0 to 60.0 seconds
conn = sqlite3.connect(DB_PATH, timeout=60.0)
conn.execute("PRAGMA busy_timeout=60000;")
```