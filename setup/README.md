# 🔐 S.I.L.O. Authentication Seeding (`setup/`)

The biggest hurdle in automated algorithmic auditing is bypassing modern anti-bot login protections. Platforms like Google, Yahoo, and TikTok will instantly flag and block scripted login attempts. 

The S.I.L.O. framework solves this using **Untethered Seeding** (`seed_master.py`). This script launches a native, fingerprint-clean Chromium browser that allows you to manually log into all the required websites just like a normal human. Once you close the browser, the script extracts your session cookies, LocalStorage, and authentication tokens into a JSON state file. The S.I.L.O. Orchestrator then uses this state file to bypass login screens entirely during the automated simulation.

---

## 🛠️ Scaling the Experiment (Adding More Personas)

By default, S.I.L.O. tests 1 Experimental persona (SSO) and 1 Control persona (Unique Passwords). However, if your local machine has the hardware resources (RAM/CPU) to support more concurrent browser instances, you can easily scale the size of your cohorts.

To add more personas to the simulation, simply open `seed_master.py` and expand the `PERSONA_CONFIG` dictionary to create larger experimental and control groups.

### Configuration Structure:
* `name`: The display name of the persona (used in logging and reports).
* `path`: The directory where the physical browser cache/profile will be stored.
* `json_out`: Where the final authentication state file will be saved.
* `sso`: A boolean (`True` or `False`). If `True`, the script will anchor the browser with a centralized identity provider (like Google). If `False`, it will prompt the decentralized unique-password flow.

### Example Scaled Configuration:

```python
PERSONA_CONFIG = {
    # --- EXPERIMENTAL COHORT (Centralized / SSO) ---
    "1": {
        "name": "Angela_SSO", 
        "path": "sessions/angela_sso_v2",
        "json_out": "config/angela_master_state.json",
        "sso": True
    },
    "2": {
        "name": "David_SSO", 
        "path": "sessions/david_sso",
        "json_out": "config/david_master_state.json",
        "sso": True
    },
    
    # --- CONTROL COHORT (Decentralized / Unique Passwords) ---
    "3": {
        "name": "Michelle_Unique", 
        "path": "sessions/michelle_unique_v2",
        "json_out": "config/michelle_unique.json",
        "sso": False
    },
    "4": {
        "name": "Sarah_Unique", 
        "path": "sessions/sarah_unique",
        "json_out": "config/sarah_unique.json",
        "sso": False
    }
}
```
*Note: If you add new personas here, remember to also add them to the `sequential_orchestrator.py` run list and define their `interests_wordlist.txt` triggers in the `config/` folder!*

---

## 🚀 How to Execute the Seeding Process

You must run this process individually for every persona in your configuration before starting the automated simulation.

**1. Launch the Seeder:**
```bash
python setup/seed_master.py
```

**2. Select the Persona:**
The terminal will prompt you to select the persona you want to seed (e.g., press `1` for Angela_SSO).

**3. Manually Authenticate:**
A Chromium browser will open automatically, pre-loaded with tabs for all your Target Domains.
* **If seeding an SSO Persona:** Log into the anchor provider (e.g., Google) first. Then go to every other tab and click "Sign in with Google."
* **If seeding a Unique Password Persona:** Use your unique credentials to log in manually on every single tab.

**4. Save the State:**
Once you have successfully authenticated on *every* tab, **manually click the 'X' to close the browser window.** The script will automatically detect the closure, compile the authentication data, and save it to the specified `json_out` path.