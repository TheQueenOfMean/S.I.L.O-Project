import os
import sys
import sqlite3
import asyncio
import pandas as pd
import pingouin as pg
from loguru import logger
from datetime import datetime
from transformers import pipeline
import json
import glob
import hashlib

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.join(PROJECT_ROOT, "results", "silo_audit.db")
INTERESTS_PATH = os.path.join(PROJECT_ROOT, "config", "interests_wordlist.txt")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# --- AI INITIALIZATION ---
EVAL_MODEL_NAME = "cross-encoder/nli-distilroberta-base"
logger.info(f"Loading Zero-Shot AI Model (Strict Mode): {EVAL_MODEL_NAME}...")

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

classifier = pipeline("zero-shot-classification", model=EVAL_MODEL_NAME)

def clean_and_load_file(filepath):
    if not os.path.exists(filepath):
        logger.warning(f" [!] File not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    items = []
    for line in lines:
        if "]" in line and "source:" in line:
            clean_line = line.split("]")[-1].strip()
        else:
            clean_line = line.strip()
        if clean_line:
            items.append(clean_line)
    return items

RAW_INTERESTS = clean_and_load_file(INTERESTS_PATH)

def get_persona_context(persona_name):
    display_name = persona_name.replace("_SSO", "").replace("_Unique", "").lower()
    traits = ""
    for line in RAW_INTERESTS:
        if ":" in line or "=" in line:
            sep = ":" if ":" in line else "="
            name, vals = line.split(sep, 1)
            if name.strip().lower() == display_name:
                traits = vals.strip()
                break
    if not traits:
        traits = "beauty, luxury, lifestyle, and fitness"
    return traits[:100]

def ingest_json_data(conn):
    if not os.path.exists(DATA_DIR): return

    json_files = glob.glob(os.path.join(DATA_DIR, "**", "*.json"), recursive=True)
    if not json_files: return

    logger.info(f"    [📥] Found {len(json_files)} JSON files. Syncing with database...")
    cursor = conn.cursor()
    
    imported_count = 0
    for file_path in json_files:
        inferred_platform = os.path.basename(os.path.dirname(file_path)).capitalize()
        if inferred_platform.lower() == "data": 
            inferred_platform = "Unknown_Platform"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                
            if isinstance(records, dict): records = [records]
                
            for rec in records:
                if not isinstance(rec, dict): continue
                
                content_text = rec.get("content_text", "")
                if not content_text:
                    data_payload = rec.get("data", {})
                    if isinstance(data_payload, list):
                        content_text = " | ".join(str(x) for x in data_payload)
                    elif isinstance(data_payload, dict):
                        content_text = data_payload.get("content", data_payload.get("query", data_payload.get("url", str(data_payload))))
                    else:
                        content_text = str(data_payload)
                        
                if not content_text or content_text == "{}": continue 
                
                pk_id = rec.get("pk_id")
                if not pk_id:
                    content_hash = hashlib.md5(content_text.encode('utf-8')).hexdigest()[:10]
                    pk_id = f"json_{content_hash}"
                
                session_id = rec.get("session_id", rec.get("session", "json_import"))
                persona_name = rec.get("persona_name", "Unknown_Persona")
                platform = rec.get("platform", inferred_platform)
                source_author = rec.get("source_author", "JSON_Sniffer")
                event_type = rec.get("event_type", rec.get("event", "ORGANIC_FEED_ITEM"))
                interaction_state = rec.get("interaction_state", "UNRECORDED")
                is_ad = rec.get("is_ad", 0)
                captured_at = rec.get("captured_at", rec.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
                cursor.execute('''
                    INSERT OR IGNORE INTO Post 
                    (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad, captured_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pk_id, session_id, persona_name, platform, content_text, source_author, event_type, interaction_state, is_ad, captured_at))
                
                if cursor.rowcount > 0: imported_count += 1
                    
        except Exception as e:
            logger.error(f"    [!] Failed to ingest {os.path.basename(file_path)}: {e}")
            
    conn.commit()
    if imported_count > 0:
        logger.success(f"    [✅] Successfully imported {imported_count} new records from JSON files.")

def sanitize_platforms(conn):
    """
    DATA HYGIENE: Mutates all platform names in the SQLite database to strictly 
    match the 6 core Sniffer platform names, cleaning up Humanizer fragmentation.
    """
    logger.info("    [🧹] Cleaning database platform names to match Sniffer truth data...")
    cursor = conn.cursor()
    cursor.execute("UPDATE Post SET platform = 'Google' WHERE platform LIKE '%Google%'")
    cursor.execute("UPDATE Post SET platform = 'Yahoo' WHERE platform LIKE '%Yahoo%'")
    cursor.execute("UPDATE Post SET platform = 'TikTok' WHERE platform LIKE '%TikTok%' OR platform LIKE '%Tiktok%'")
    cursor.execute("UPDATE Post SET platform = 'YouTube' WHERE platform LIKE '%YouTube%' OR platform LIKE '%Youtube%'")
    cursor.execute("UPDATE Post SET platform = 'Reddit' WHERE platform LIKE '%Reddit%'")
    cursor.execute("UPDATE Post SET platform = 'X Timeline' WHERE platform LIKE '%X%' OR platform LIKE '%Twitter%'")
    conn.commit()

async def score_post_relevance(content, persona_name):
    try:
        if not content or not str(content).strip(): return 1
        snippet = str(content).strip()[:300]
        context = get_persona_context(persona_name)
        
        highly_targeted = f"exclusively targeted to niche interests in {context}"
        broad_content = "general mainstream content, broad lifestyle, or neutral information"
        unrelated = "completely unrelated to the user's profile"
        
        labels = [highly_targeted, broad_content, unrelated]
        result = await asyncio.to_thread(classifier, snippet, labels)
        
        confidence = result["scores"][result["labels"].index(highly_targeted)]
        broad_confidence = result["scores"][result["labels"].index(broad_content)]
        
        if confidence > 0.70 and confidence > broad_confidence: return 5
        elif confidence > 0.40 or broad_confidence > 0.50: return 3
        else: return 1
    except Exception as e:
        return 1

async def run_reliability_audit(conn, limit=10):
    logger.info(f"[🔍] Phase 5: Starting AI Reliability Audit with {EVAL_MODEL_NAME}...")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ReliabilityInterpretation (pk_id TEXT, score INTEGER, session INTEGER, theme TEXT)")
    cursor.execute("SELECT pk_id, content_text, persona_name FROM Post WHERE pk_id NOT IN (SELECT pk_id FROM ReliabilityInterpretation) LIMIT ?", (limit,))
    
    posts = cursor.fetchall()
    if not posts: return
    
    for pk_id, content, persona in posts:
        for session_id in range(1, 6):
            try:
                score = await score_post_relevance(content, persona)
                cursor.execute("INSERT INTO ReliabilityInterpretation (pk_id, score, session, theme) VALUES (?, ?, ?, ?)", (pk_id, score, session_id, "Reliability_Check"))
                conn.commit()
            except Exception: pass

def calculate_cronbach_alpha(conn):
    try:
        df = pd.read_sql_query("SELECT pk_id, session, score FROM ReliabilityInterpretation", conn)
        if df.empty or len(df["session"].unique()) < 2: return 0.0
        pivot_df = df.pivot_table(index="pk_id", columns="session", values="score", aggfunc="mean")
        return pg.cronbach_alpha(data=pivot_df)[0]
    except Exception: return 0.0

async def score_all_remaining_posts(conn):
    logger.info("[🚀] Phase 6: Scoring remaining posts using Strict Mode...")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS Interpretation (pk_id TEXT PRIMARY KEY, score INTEGER, theme TEXT)")
    cursor.execute("SELECT pk_id, content_text, persona_name FROM Post WHERE pk_id NOT IN (SELECT pk_id FROM Interpretation)")
    
    posts = cursor.fetchall()
    if not posts: 
        logger.info("    [~] No un-scored posts remaining.")
        return
    
    total = len(posts)
    count = 0
    for pk_id, content, persona in posts:
        try:
            score = await score_post_relevance(content, persona)
            cursor.execute("INSERT INTO Interpretation (pk_id, score, theme) VALUES (?, ?, ?)", (pk_id, score, "General_Audit"))
            conn.commit() 
            
            count += 1
            if count % 50 == 0: logger.info(f"    [🤖] Progress: Scored {count}/{total} posts...")
        except Exception: pass
            
    logger.success(f"    [✅] Successfully scored all {total} posts!")

def generate_text_report(conn, alpha):
    report_path = os.path.join(PROJECT_ROOT, "results", "reports", "final_silo_drift_report.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    sql_query = """
        SELECT 
            p.platform, 
            COALESCE(p.interaction_state, 'UNRECORDED') as interaction,
            p.event_type as content_type, 
            p.persona_name, 
            ROUND(AVG(i.score), 2) as avg_relevance, 
            COUNT(*) as post_count,
            COUNT(DISTINCT p.source_author) as distinct_authors
        FROM Post p 
        JOIN Interpretation i ON p.pk_id = i.pk_id 
        GROUP BY p.platform, p.persona_name, p.event_type, p.interaction_state
    """
    raw_df = pd.read_sql_query(sql_query, conn)
    
    total_sql = """
        SELECT 
            p.persona_name, 
            ROUND(AVG(i.score), 2) as grand_total_relevance 
        FROM Post p 
        JOIN Interpretation i ON p.pk_id = i.pk_id 
        GROUP BY p.persona_name
    """
    total_df = pd.read_sql_query(total_sql, conn)
    
    timeline_sql = """
        WITH ChronoData AS (
            SELECT 
                p.persona_name, 
                COALESCE(p.interaction_state, 'UNRECORDED') || ' - ' || p.event_type as type, 
                i.score, 
                NTILE(4) OVER (PARTITION BY p.persona_name, p.event_type, p.interaction_state ORDER BY p.captured_at ASC) as session_stage 
            FROM Post p 
            JOIN Interpretation i ON p.pk_id = i.pk_id
        ) 
        SELECT persona_name, type, session_stage, ROUND(AVG(score), 2) as stage_avg_score 
        FROM ChronoData 
        GROUP BY persona_name, type, session_stage
    """
    timeline_df = pd.read_sql_query(timeline_sql, conn)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=========================================================\n")
        f.write("S.I.L.O. Phase 5: Recommendation Drift Report (Transformers AI - Strict Mode)\n")
        f.write("=========================================================\n")
        f.write(f"Generated at: {datetime.now()}\n")
        f.write(f"Cronbach Alpha (α): {alpha:.4f}\n\n")

        if raw_df.empty:
            f.write("No data available in database.\n")
            return

        valid_personas = [p for p in raw_df['persona_name'].unique() if p not in ["Unknown", "Unknown_Persona", "json_import"]]

        for persona in valid_personas:
            f.write(f"\n{'='*60}\n")
            f.write(f"PERSONA ANALYSIS: {persona}\n")
            f.write(f"{'='*60}\n\n")

            f.write("--- PLATFORM & INTERACTION BREAKDOWN ---\n")
            persona_raw = raw_df[raw_df['persona_name'] == persona].copy()
            if not persona_raw.empty:
                display_df = persona_raw[['platform', 'interaction', 'content_type', 'avg_relevance', 'post_count', 'distinct_authors']]
                display_df.columns = ['Platform', 'Interaction', 'Content Type', 'Avg Score', '# Posts', '# Authors']
                f.write(display_df.to_string(index=False) + "\n\n")

            f.write("--- CHRONOLOGICAL DRIFT VELOCITY ---\n")
            persona_timeline = timeline_df[timeline_df['persona_name'] == persona].copy()
            if not persona_timeline.empty:
                drift_pivot = persona_timeline.pivot_table(index="type", columns="session_stage", values="stage_avg_score")
                drift_pivot.columns = [f"Stage {col}" for col in drift_pivot.columns]
                drift_pivot = drift_pivot.astype(object).fillna("-").infer_objects(copy=False)
                f.write(drift_pivot.to_string() + "\n\n")
            
            f.write("--- FINAL TALLY ---\n")
            final_score = total_df[total_df['persona_name'] == persona]['grand_total_relevance'].values
            if len(final_score) > 0:
                f.write(f"Total Average Relevance Score: {final_score[0]:.2f} / 5.00\n\n")

        f.write(f"\n{'='*60}\n")
        f.write("COMPARISON SUMMARY (DRIFT DELTA)\n")
        f.write(f"{'='*60}\n\n")
        
        valid_totals = total_df[total_df['persona_name'].isin(valid_personas)]
        
        if len(valid_totals) >= 2:
            sorted_totals = valid_totals.sort_values(by='grand_total_relevance', ascending=False).reset_index(drop=True)
            
            p1_name = sorted_totals.iloc[0]['persona_name']
            p1_score = sorted_totals.iloc[0]['grand_total_relevance']
            p2_name = sorted_totals.iloc[1]['persona_name']
            p2_score = sorted_totals.iloc[1]['grand_total_relevance']
            diff = p1_score - p2_score
            
            f.write(f"1. Most Aligned Feed: {p1_name} ({p1_score:.2f})\n")
            f.write(f"2. Runner-Up: {p2_name} ({p2_score:.2f})\n\n")
            f.write(f"Calculated Delta: {diff:.2f} points\n\n")
            f.write(f"Analysis: '{p1_name}' receives recommendations more tightly aligned with their core interests than '{p2_name}' by a margin of {diff:.2f} points.\n")
            f.write("When interactions are captured (CLICKED states vs VIEWED states), larger deltas usually indicate that active feedback loops heavily steer algorithm drift.\n")
        else:
            f.write("Analysis: Multiple personas must be simulated to generate a comparison delta.\n")
            
    logger.success(f"Report saved: {report_path}")

async def run_full_audit():
    if not os.path.exists(DB_PATH): 
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Post (
        id INTEGER PRIMARY KEY, pk_id TEXT UNIQUE, session_id TEXT, persona_name TEXT, 
        platform TEXT, content_text TEXT, source_author TEXT, event_type TEXT, 
        interaction_state TEXT, is_ad BOOLEAN, captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    
    ingest_json_data(conn)
    
    # NEW STEP: Sanitize fragmented platform names
    sanitize_platforms(conn)
    
    await run_reliability_audit(conn, limit=10)
    await score_all_remaining_posts(conn)
    
    alpha = calculate_cronbach_alpha(conn)
    generate_text_report(conn, alpha)
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(run_full_audit())