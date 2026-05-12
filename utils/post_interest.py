import os
from loguru import logger
from utils.telemetry import BASE_DIR

def load_interest_trigger_list(persona_name=None):
    """Reads the interest wordlist and extracts keywords for the bots."""
    path = os.path.join(BASE_DIR, "config", "interests_wordlist.txt")
    try:
        if not os.path.exists(path):
            logger.warning(f"    [⚠️] Interest Manager: {path} not found. Skipping interest checks.")
            return []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        trigger_words = []
        for line in lines:
            # Clean out the "" artifact
            if "]" in line and "source:" in line.lower():
                line = line.split("]")[-1]

            line = line.strip().lower()
            if not line: continue

            # Check for Persona Prefixes (e.g., Angela: soft girl)
            if ":" in line or "=" in line:
                sep = ":" if ":" in line else "="
                name, vals = line.split(sep, 1)

                if persona_name:
                    clean_name = persona_name.replace("_sso", "").replace("_unique", "").lower()
                    if clean_name in name.strip():
                        trigger_words.extend([w.strip() for w in vals.split(",") if w.strip()])
                else:
                    trigger_words.extend([w.strip() for w in vals.split(",") if w.strip()])
            
            # Handle Vertical Universal Lists
            else:
                if "," in line:
                    trigger_words.extend([w.strip() for w in line.split(",") if w.strip()])
                else:
                    trigger_words.append(line)

        return trigger_words
    except Exception as e:
        logger.error(f"Error loading interests: {e}")
        return []

def is_interested_in(text, persona_name=None):
    """
    Helper function to quickly check if a block of text matches a persona's interests.
    Use this in your nav files to quickly test tweets/posts!
    """
    if not text:
        return False
    
    triggers = load_interest_trigger_list(persona_name)
    text_lower = text.lower()
    return any(word in text_lower for word in triggers)