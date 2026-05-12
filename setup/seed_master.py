import asyncio
import os
import subprocess
import sys
from patchright.async_api import async_playwright

# --- PATH INJECTOR ---
# Force Python to look one level up since this script is inside the /setup folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# DYNAMIC IMPORT: Pulling the target domains directly from your registry
from core.platforms.registry import PLATFORMS

# --- CONFIGURATION ---
PERSONA_CONFIG = {
    "1": {
        "name": "Angela_SSO", 
        "path": "sessions/angela_sso_v2",  # <-- FIXED
        "json_out": "config/angela_master_state.json",
        "sso": True
    },
    "2": {
        "name": "Michelle_Unique", 
        "path": "sessions/michelle_unique_v2", # <-- FIXED
        "json_out": "config/michelle_unique.json",
        "sso": False
    }
}

async def get_browser_path():
    """Forces the script to use Playwright's internal Chromium to prevent Downgrade Crashes."""
    async with async_playwright() as p:
        chromium_path = p.chromium.executable_path
        print(f"[*] Enforcing strict Chromium version match: {chromium_path}")
        return chromium_path

async def extract_state_to_json(user_data_dir, json_out_path):
    """Silently boots up the profile folder and rips the cookies into a JSON file."""
    print("\n[*] Compiling physical session data into JSON format for the bots...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True
        )
        os.makedirs(os.path.dirname(json_out_path), exist_ok=True)
        await context.storage_state(path=json_out_path)
        await context.close()
    print(f"[+] SUCCESS: State exported to {json_out_path}!")

async def seed_profile_untethered(config, browser_path):
    persona_name = config["name"]
    folder_path = config["path"]
    json_out_path = config["json_out"]
    is_sso = config["sso"]

    # Resolve paths
    base_dir = os.path.dirname(os.getcwd()) if os.getcwd().endswith('setup') else os.getcwd()
    full_path = os.path.join(base_dir, folder_path)
    full_json_path = os.path.join(base_dir, json_out_path)
    os.makedirs(full_path, exist_ok=True)

    print(f"\n[!!!] STARTING UNTETHERED SEEDING FOR: {persona_name.upper()}")
    print(f"[*] Physical Directory: {full_path}")
    print("[*] Launching browser natively via Windows (Zero Automation Engine)...")

    # Base Arguments
    args = [
        browser_path,
        f"--user-data-dir={full_path}",
        "--start-maximized",
        "--password-store=basic",
    ]

    # 1. Add the primary anchor accounts first so they open in the first tabs
    if is_sso:
        args.append("https://accounts.google.com")
    else:
        args.append("https://login.yahoo.com")
        args.append("https://accounts.google.com") # Michelle still needs Google for YouTube

    # 2. Dynamically inject the remaining URLs straight from your S.O.A.P. registry
    print("[*] Pulling dynamic target list from core.platforms.registry...")
    for plat_name, plat_info in PLATFORMS.items():
        url = plat_info.get("url")
        # Prevents opening duplicate tabs if the anchor sites are already defined in the registry
        if url and "accounts.google.com" not in url and "login.yahoo.com" not in url:
            args.append(url)

    print("\n" + "="*60)
    print(f" ACTION REQUIRED FOR {persona_name}:")
    if is_sso:
        print(" -> Log into Google first. Use 'Sign in with Google' for all other sites.")
    else:
        print(" -> Use Yahoo as the anchor. Use UNIQUE passwords for all other sites.")
    print("\n 1. Complete all logins manually across the opened tabs.")
    print(" 2. Ensure every platform authenticates successfully.")
    print(" 3. When you are 100% finished, manually click the 'X' to close the browser.")
    print(" 4. This script will automatically detect when the browser closes and save the session.")
    print("="*60)

    # This blocks the script until the user physically closes the browser window
    process = subprocess.Popen(args)
    process.wait()

    print(f"\n[+] Browser closed securely.")
    
    await extract_state_to_json(full_path, full_json_path)

async def main():
    print("="*50)
    print(" PERSONA SEEDING TOOL (UNTETHERED MODE) ")
    print("="*50)
    print("1) Angela_SSO (Centralized Identity)")
    print("2) Michelle_Unique (Unique Password/Control Group)")
    print("q) Quit")
    
    choice = input("\nSelect persona to seed: ").strip()
    
    if choice in PERSONA_CONFIG:
        executable_path = await get_browser_path()
        await seed_profile_untethered(PERSONA_CONFIG[choice], executable_path)
    elif choice.lower() == 'q':
        return
    else:
        print("[!] Invalid choice.")

if __name__ == "__main__":
    asyncio.run(main())