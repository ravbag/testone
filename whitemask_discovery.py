import json
import pandas as pd
import datetime
import re
from tqdm import tqdm

# ==========================================
# EXPERIMENTATION ZONE
# ==========================================
DREARY_TOKENS = {"meditative", "contemplative", "unhurried", "pacing", "slow burn"}
DREARY_PENALTY = 15.0  # Increased to push 'festival' fluff down
REGIONAL_SURCHARGE = {"Japan": 5.0, "South Korea": 5.0, "Hong Kong": 5.0}
MIN_SCORE_THRESHOLD = 20.0 
# ==========================================

def super_clean(t):
    """The 'Nuclear Option' for title matching: removes EVERYTHING but letters and numbers."""
    if not isinstance(t, str): return ""
    return re.sub(r'[^a-z0-9]', '', t.lower())

def parse_rating(r_str):
    try: return float(str(r_str).split()[0])
    except: return 0.0

def run():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    print(f"--- Whitemask V8: Surgical Discovery ---")
    
    # 1. LOAD FINGERPRINT
    fp_path = "whitemask_fingerprint_latest.csv"
    if not os.path.exists(fp_path):
        print(f"Error: {fp_path} not found. Run Autopsy first.")
        return
    
    fp = pd.read_csv(fp_path)
    # We consolidate the score for simpler discovery matching
    weights = dict(zip(fp['motif'], fp['score']))
    
    # 2. LOAD HISTORY & EXTRACT SINCERE CREATORS
    my_df = pd.read_csv("films.csv")
    # Build a clean 'Seen' dictionary
    seen_dict = {super_clean(row['Name']): str(row['Year']) for _, row in my_df.iterrows()}
    
    # Pre-scan for Legacy Creators (Auto-detecting Miike, Kitano, etc.)
    favored_creators = set()
    print("Pre-scanning for Legacy Creators...")
    with open("fulldump.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            movie = json.loads(line)
            m_title = super_clean(movie.get('title', ''))
            m_year = str(movie.get('year', ''))
            if m_title in seen_dict and seen_dict[m_title] == m_year:
                for d in movie.get('directors', []): favored_creators.add(d)
                for c in movie.get('cast', [])[:5]: favored_creators.add(c)

    # 3. THE DISCOVERY SCAN
    results = []
    processed_keys = set() # To stop duplicates like the Ichi double-entry

    with open("fulldump.jsonl", 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Scanning"):
            movie = json.loads(line)
            title_raw = movie.get('title', '')
            title_sc = super_clean(title_raw)
            year = str(movie.get('year', ''))
            movie_key = f"{title_sc}|{year}"

            # A: PREVENT SEEN FILMS
            if title_sc in seen_dict and seen_dict[title_sc] == year:
                continue
            
            # B: PREVENT DUPLICATES
            if movie_key in processed_keys:
                continue
            processed_keys.add(movie_key)

            # C: SCORE CALCULATION
            synopsis = movie.get('synopsis', '').lower()
            reviews = [r.get('review_text', '').lower() for r in (movie.get('reviews', []) or [])[:3]]
            combined_text = synopsis + " " + " ".join(reviews)
            
            score = 0
            matching = []
            for motif, w in weights.items():
                if motif in combined_text:
                    score += w
                    matching.append(motif)

            # D: SURCHARGES & PENALTIES
            for dreary in DREARY_TOKENS:
                if dreary in combined_text: score -= DREARY_PENALTY
            
            # Regional
            countries = " ".join(movie.get('countries', []))
            for reg, boost in REGIONAL_SURCHARGE.items():
                if reg in countries: score += boost
            
            # Legacy Hit check
            creators = set(movie.get('directors', []) + movie.get('cast', []))
            legacy_found = any(p in favored_creators for p in creators)
            if legacy_found: score += 10.0 # High reward for Sincere Legacy

            if score > MIN_SCORE_THRESHOLD:
                results.append({
                    "Name": title_raw,
                    "Year": year,
                    "Score": round(score, 2),
                    "URL": movie.get('url'),
                    "Legacy": "YES" if legacy_found else "NO",
                    "Evidence": " | ".join(matching[:5])
                })

    # FINAL OUTPUT
    filename = f"whitemask_thunderbolts_{timestamp}.csv"
    pd.DataFrame(results).sort_values("Score", ascending=False).to_csv(filename, index=False)
    print(f"Done. Check {filename} for your Thunderbolts.")

if __name__ == "__main__":
    import os
    run()