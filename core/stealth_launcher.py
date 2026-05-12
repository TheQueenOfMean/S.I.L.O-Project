import os
from patchright.async_api import async_playwright

class StealthLauncher:
    @staticmethod
    async def launch_persona_context(profile_dir, headless=True):
        """
        Launches a persistent context mirroring the Seed Master's 'Untethered' logic.
        """
        playwright_lib = await async_playwright().start()
        
        # --- 🛠️ THE FIX: Mirroring the strict versioning logic from seed_master.py ---
        executable_path = playwright_lib.chromium.executable_path
        
        # Absolute path resolution to ensure it hits the same folder seeded by seed_master
        abs_profile_path = os.path.abspath(profile_dir)

        # Syncing arguments exactly with the seed_master logic
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--password-store=basic",
            "--start-maximized",
        ]

        # Use launch_persistent_context to load the full storage state (cookies/LocalStorage)
        context = await playwright_lib.chromium.launch_persistent_context(
            user_data_dir=abs_profile_path,
            executable_path=executable_path, # <-- MATCHES SEED_MASTER EXACTLY
            headless=headless,
            args=args,
            ignore_default_args=["--enable-automation"], # Masks the bot signature
            viewport={"width": 1280, "height": 720}
        )

        return context, playwright_lib

    @staticmethod
    async def close_all(context, playwright_lib):
        if context:
            await context.close()
        if playwright_lib:
            await playwright_lib.stop()