# S.I.L.O. (Single-Identity Loop Observation)

![Version](https://img.shields.io/badge/version-2026.5-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Playwright](https://img.shields.io/badge/Patchright-Stealth-green)
![AI](https://img.shields.io/badge/Transformers-Zero_Shot-orange)

**Author:** Madeleine Gonzalez  
**Institution:** Roosevelt University  
**Degree:** Master of Science in Cyber Security and Information Assurance  
**Supervising Faculty:** Professor Rami | Dr. Jerry Schnepp, PhD  

---

## 📌 Executive Summary
S.I.L.O. is an automated, stealth-based browser orchestration framework. Operating entirely within a localized, hardware-restricted environment, the framework audits and quantifies **Cross-Domain Recommendation Drift** using local Zero-Shot AI classification models.

The primary objective of this research is to measure the impact of identity centralization and password reuse on algorithmic behavior. Specifically, the framework tests the hypothesis that centralized identities (Single Sign-On) and reused credentials accelerate the creation of algorithmic filter bubbles compared to decentralized, unique-password browsing. By injecting controlled, randomized browsing patterns and intercepting the resulting algorithmic payloads, S.I.L.O. provides both quantitative engagement metrics and qualitative AI-driven trajectory reports.

## 🧠 Core Methodologies & Concepts
* **Independent Variables:** The simulation tests two primary control variables across the personas:
  1. **Credential Strategy:** Centralized SSO and password reuse vs. Decentralized unique passwords.
  2. **Anchor Engine:** The Google ecosystem vs. The Yahoo ecosystem.
* **Recommendation Drift:** The measurable rate at which an algorithm shifts a user's content feed from general/trending topics to hyper-specific interest silos based on behavioral signals.
* **The S.I.L.O. Control Group:** To ensure tight experimental control, the engine evaluates exactly **2 personas** navigating across **8 Target Domains** (Google Search, Google News, YouTube, Yahoo Search Feed, Yahoo News, TikTok, X/Twitter, and Reddit):
  * **Angela Hayden (Experimental Group):** Centralized Identity / Password Reuse / Anchored via Google SSO.
  * **Michelle Owens (Control Group):** Decentralized Identity / Unique Passwords / Anchored via Yahoo.

---

## 🏗️ System Architecture & Telemetry

S.I.L.O. bypasses modern anti-bot protections to gather raw data directly from the network layer across 8 distinct Target Domains.

### 1. The Stealth Orchestrator (/core & /utils)
Utilizes Patchright (a stealth-focused fork of Playwright) running native Chromium to launch undetectable contexts on a local laptop environment. 
* **Untethered Seeding (seed_master.py):** A pre-execution tool that dynamically pulls from the Target Domain registry, opening all required targets to allow secure manual authentication before saving the cookie states to JSON.
* **The Custom Humanizer (humanizer.py):** Replaces basic automation with biometric simulation. Features randomized scrolling velocity, varied typing cadence, dynamic wordlist querying, and "distracted" multi-tab switching to avoid bot-mitigation triggers.

### 2. Network Interception & Telemetry (/sniffers & telemetry.py)
Rather than relying on brittle HTML scraping, S.I.L.O. uses passive asynchronous sniffers to capture raw algorithm logic.
* **Payload Interception:** Scripts intercept underlying API calls (e.g., FYP batches, search results) before they render in the browser DOM.
* **SQLite Master Telemetry:** All humanizer actions (clicks, searches, interactions) and session metadata are synchronously logged to a local relational SQLite database (`silo_audit.db`) operating in WAL mode for precise chronological auditing.

### 3. The Analytics Pipeline (/analytics)
Transforms raw, chaotic web data into academic-grade thesis reports.
* **data_janitor.py:** Applies intra-session deduplication to normalize and preserve unique post captures across historical runs.
* **aequitas_bridge.py:** The quantitative engine. Generates baseline metrics, calculating action distribution and multi-domain engagement volume, outputting a behavioral matrix CSV.
* **silo_analyzer_zeroshot.py:** The qualitative auditor. Leverages a local Hugging Face transformer model (`cross-encoder/nli-distilroberta-base`) and Cronbach's Alpha to analyze data snapshots, generating comprehensive text reports detailing the velocity of content silo formation without relying on external cloud APIs.

---

## 🖥️ Hardware & Network Requirements 

* **Resource Scaling:** S.I.L.O. is intentionally designed to run on a standard local machine with limited resources (currently utilizing 2 personas to accommodate standard laptop hardware). However, the engine is highly scalable and can be modified to orchestrate additional concurrent personas on more powerful local machines.
* **Residential IP Mandate:** This experiment **cannot** be executed using cloud service providers (e.g., AWS, Google Cloud, Azure, DigitalOcean). The target websites actively monitor traffic origins and will automatically block or sandbox requests coming from known datacenter IP addresses. **A local, residential IP address is strictly required** for the stealth engine to operate properly without triggering aggressive anti-bot defenses or CAPTCHA loops.

---

## ⚙️ Prerequisites & Setup

1. Environment: Python 3.12 running locally.
2. Virtual Environment Initialization:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3. Dependencies Installation:
    ```bash
    pip install -r requirements.txt
    patchright install chromium
    ```

---

## 🚀 Execution Guide

### Phase 0: System & Persona Configuration
Before running the simulation, you must manually set up your personas and define their behavioral triggers:
1. **Account Creation & Credential Strategy:** You must manually create the foundational accounts for your personas before seeding them into the S.I.L.O. engine:
    * **Experimental Group (SSO):** Create an email account with a major SSO provider (e.g., Google), or use an email to create an SSO hub (like Facebook). You will use this single identity to authenticate across all target websites.
    * **Control Group (Unique):** Create an email account with a non-SSO provider. You must manually register individual accounts on every target website, ensuring you generate and use a **unique password** for each platform.
2. **`core/platforms/registry.py` (Target Domains):** This registry defines the 8 default target websites and their DOM selectors (Google Search, Google News, YouTube, Yahoo Search Feed, Yahoo News, TikTok, X/Twitter, and Reddit). You can easily customize this file to add new websites or test different SSO providers.
3. **`config/wordlist.txt` (Search Queries):** A line-by-line list of search terms. The S.I.L.O. engine randomly selects from this list to simulate organic search behavior across the various platforms.
4. **`config/interests_wordlist.txt` (Engagement Triggers):** A list of keywords or phrases that define the core interests of your personas. The engine cross-references this list against intercepted post titles and metadata to mathematically determine if the bot should click a post, watch a video, or leave a "Like". *(Note: You can specify interests per persona using the format `persona_name: interest1, interest2`)*.

### Phase 1: Authentication Seeding
Initialize the authentication states using the native Chromium bypass.
    
    python setup/seed_master.py

### Phase 2: System Smoke Test (Verification)
Prior to launching the main simulation, execute the 30-minute sequential smoke test (15 minutes per persona) to validate that the SQLite database is initializing and network sniffers are intercepting JSON payloads.

    python test_run.py

### Phase 3: Data Collection (Local Execution)
Execute the main orchestrator to begin the full 1-hour simulation. 
    
    python sequential_orchestrator.py

Menu Options:
* [1] Angela Only: 30-minute deep dive into centralized identity recommendation drift.
* [2] Michelle Only: 30-minute control baseline generation.
* [3] Sequential Run: Runs Angela (30 mins) -> Cleans RAM -> Runs Michelle (30 mins). Total runtime: 1 Hour.

### Phase 4: Analytics & Reporting
Note: Ensure both the experimental and control sessions are complete before running the analytics suite.

Generate Quantitative Baselines & AI Drift Reports:
    
    python analytics/aequitas_bridge.py
    python analytics/silo_analyzer_zeroshot.py

All final markdown reports and CSV datasets are output directly to the `/results/reports/` directory.

---

## ⚠️ Disclaimer & Ethical Considerations
This framework was developed strictly for academic research regarding data privacy and algorithmic transparency. It operates using authorized test personas within a localized, hardware-restricted environment and respects the rate limits of the Target Domains by utilizing humanized interaction delays.
---

## 🐳 Advanced Scaling (Docker & Containerization)

For researchers looking to scale the experiment to dozens or hundreds of concurrent personas, virtual environments on a single laptop will quickly hit hardware limits. Containerizing S.I.L.O. allows you to orchestrate massive parallel cohorts.

### The Two Deployment Paths

**1. Academic HPC & On-Premise Labs (Ideal)**
If you are deploying Docker on a university supercomputer, an on-premise research cluster, or a powerful home server, you have the optimal setup. As long as the network exits through a standard institutional or residential ISP, you can scale to hundreds of containers natively without triggering datacenter bot-mitigation defenses.

**2. Commercial Cloud Deployments (Proxies Required)**
**⚠️ CRITICAL WARNING:** If you deploy these containers to commercial cloud providers (AWS, Google Cloud, Azure, DigitalOcean), target platforms like TikTok and X will instantly sandbox or blacklist your datacenter IPs. To run S.I.L.O. in the cloud, you **MUST** route your browser traffic through a Residential Proxy Network.

---

### 1. Dockerfile Configuration
Because S.I.L.O. utilizes Patchright (a stealth Playwright fork) and native Chromium, your Docker container must use the official Playwright base image to ensure all system-level browser dependencies (codecs, fonts, etc.) are present.

Create a `Dockerfile` in your root directory:

```dockerfile
# Use the official Playwright Python image to get system browser dependencies
FROM [mcr.microsoft.com/playwright/python:v1.44.0-jammy](https://mcr.microsoft.com/playwright/python:v1.44.0-jammy)

# Set the working directory
WORKDIR /app

# Copy the requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Patchright's stealth Chromium build
RUN patchright install chromium

# Copy the rest of the framework into the container
COPY . .

# Default command to run the simulation
CMD ["python", "sequential_orchestrator.py"]
```

### 2. Docker Compose (Multi-Persona Orchestration)
To run multiple cohorts simultaneously without manual terminal management, use `docker-compose`. This isolates your Experimental (SSO) and Control (Unique) groups into separate containers while sharing the same underlying SQLite database.

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  silo_sso_cohort:
    build: .
    volumes:
      # Mount your local directories to prevent data loss when containers spin down
      - ./results:/app/results
      - ./sessions:/app/sessions
      - ./data:/app/data
    environment:
      - COHORT_MODE=SSO_ONLY
      # Only required if deploying to a cloud server:
      - RESIDENTIAL_PROXY=[http://user:pass@proxy.provider.com:8000](http://user:pass@proxy.provider.com:8000)

  silo_unique_cohort:
    build: .
    volumes:
      - ./results:/app/results
      - ./sessions:/app/sessions
      - ./data:/app/data
    environment:
      - COHORT_MODE=UNIQUE_ONLY
      - RESIDENTIAL_PROXY=[http://user:pass@proxy.provider.com:8001](http://user:pass@proxy.provider.com:8001)
```

### 3. Integrating Proxies (For Cloud Deployments Only)
If your environment requires proxies to bypass datacenter IP bans, you must inject the proxy environment variable into the Chromium launcher. Update `launch_persona_context` inside `core/stealth_launcher.py`:

```python
# Inside stealth_launcher.py
proxy_url = os.getenv("RESIDENTIAL_PROXY")
proxy_config = {"server": proxy_url} if proxy_url else None

context = await playwright_lib.chromium.launch_persistent_context(
    user_data_dir=abs_profile_path,
    executable_path=executable_path,
    headless=True,
    args=args,
    proxy=proxy_config, # Injects the residential proxy if available
    ignore_default_args=["--enable-automation"],
    viewport={"width": 1280, "height": 720}
)
```

### 4. Execution
Once your configuration is set, spin up your experimental cohorts using:
```bash
docker-compose up --build -d
```
