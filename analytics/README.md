# 📊 S.I.L.O. Analytics Pipeline

This directory contains the data processing, deduplication, and AI-scoring engines for the Single-Identity Loop Observation (S.I.L.O.) framework. 

**⚠️ CRITICAL EXECUTION TIMING:** The scripts in this folder must **only be executed AFTER** the S.I.L.O. stealth engine has finished its simulation run and safely closed the browser contexts. Running these scripts while the orchestrator is actively collecting data will cause SQLite database locks and corrupt your telemetry.

---

## ⏱️ Longitudinal Tracking (Algorithmic Drift Over Time)
While this pipeline can be used for a single 1-hour snapshot, it is designed for **longitudinal drift tracking**. 

To measure how fast an algorithm builds a filter bubble over an extended period, you should run the analytics pipeline at specific intervals (e.g., Day 1, Day 3, Day 7) during a multi-day experiment. Because S.I.L.O. logs every event with a precise chronological timestamp, running the analyzer at different intervals allows you to chart the exact velocity of recommendation drift over time.

---

## 🛠️ The Pipeline Scripts (Run in this order)

To generate an accurate drift report, you must execute the scripts in the following order:

### 1. The Data Janitor (`data_janitor.py`)
* **Purpose:** Database Hygiene and Intra-Session Deduplication.
* **How it works:** When algorithms refresh a feed (like X/Twitter or TikTok), they often push the exact same post multiple times in a single session. If left unchecked, this artificially inflates the AI's relevance score. The Data Janitor safely scrubs the `silo_audit.db` database, keeping only unique post captures per session while preserving the historical integrity of past runs.
* **Command:** `python data_janitor.py`

### 2. The Quantitative Engine (`aequitas_bridge.py`)
* **Purpose:** Behavioral baselines and volume metrics.
* **How it works:** This script acts as a bridge between the raw SQLite database and traditional data science tools. It calculates action distributions, organic-to-targeted-ad ratios, and active click volumes across all 8 target platforms. It outputs a clean `silo_behavioral_matrix.csv` file into the `/results/reports/` directory.
* **Command:** `python aequitas_bridge.py`

### 3. The Qualitative AI Auditor (`silo_analyzer_zeroshot.py`)
* **Purpose:** Calculating Recommendation Drift using Machine Learning.
* **How it works:** This is the core intelligence of the analytics suite. It uses a local Hugging Face transformer model (`cross-encoder/nli-distilroberta-base`) to evaluate the content scraped during the simulation against the persona's defined `interests_wordlist.txt`. It scores every post on a 1-to-5 relevance scale and utilizes Cronbach's Alpha to ensure statistical reliability. It outputs a comprehensive text report detailing the final "Drift Delta" between the SSO and Unique Password personas.
* **Command:** `python silo_analyzer_zeroshot.py`

---

## 📂 Output Directory
All CSV matrices and AI-generated text reports are automatically saved to the `results/reports/` directory at the root of the project.