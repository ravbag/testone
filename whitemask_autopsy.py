import json
import pandas as pd
import math
import re
import datetime
import os
from collections import Counter
from tqdm import tqdm

# --- CONFIG ---
MY_FILMS = "films.csv"
DATASET = "fulldump.jsonl"
ALPHA = 0.5
MIN_FREQ = 2 
DIRECTOR_DIVERSITY = 2 

def super_clean(t):
    if not isinstance(t, str): return ""
    return re.sub(r'[^a-z0-9]', '', t.lower())

def tokenize(text):
    if not isinstance(text, str): return []
    # FIX: Allow words as short as 2 letters (War, Pi, Go)
    return re.findall(r"\b[a-z0-9']{2,}\b", text.lower())

# Stopwords: These are allowed inside phrases, but ignored as single-word motifs
STOPWORDS = {"the", "and", "this", "that", "with", "from", "for", "was", "were", "of", "to", "in", "is", "it", "as", "on"}

def get_ngrams(text, n_range=(1, 2, 3)):
    tokens = tokenize(text)
    out = set()
    for n in n_range:
        for i in range(len(tokens) - n + 1):
            gram = " ".join(tokens[i:i+n])
            # Filter out single-word generic fluff
            if n == 1 and (gram in STOPWORDS or len(gram) < 3):
                continue
            out.add(gram)
    return out

def run():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    print(f"--- Whitemask V12: Forensic Autopsy [{timestamp}] ---")
    
    # 1. LOAD HISTORY
    my_df = pd.read_csv(MY_FILMS)
    history = {super_clean(row['Name']): int(row['Year']) for _, row in my_df.iterrows()}
    
    liked_motifs = Counter()
    base_motifs = Counter()
    motif_directors = {} 
    
    n_liked, n_base = 0, 0
    matched_titles = set()
    processed_keys = set() # To prevent double-counting motifs from duplicates

    # 2. PROCESS JSONL
    with open(DATASET, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Mining Sincerity"):
            movie = json.loads(line)
            title_sc = super_clean(movie.get('title', ''))
            try: m_year = int(movie.get('year', 0))
            except: m_year = 0
            
            # UNIQUE ID: Title + Year
            movie_key = f"{title_sc}|{m_year}"
            if movie_key in processed_keys: continue
            processed_keys.add(movie_key)
            
            # Text layers: 10 reviews + Synopsis
            text_parts = [movie.get('synopsis', ''), " ".join(movie.get('genres', []))]
            for rev in (movie.get('reviews', []) or [])[:10]:
                text_parts.append(rev.get('review_text', ''))
            
            full_text = " ".join(text_parts)
            motifs = get_ngrams(full_text)
            directors = movie.get('directors', [])

            # Matching Logic
            is_liked = False
            if title_sc in history:
                if abs(m_year - history[title_sc]) <= 1:
                    is_liked = True

            if is_liked:
                n_liked += 1
                matched_titles.add(title_sc)
                for m in motifs: 
                    liked_motifs[m] += 1
                    if m not in motif_directors: motif_directors[m] = set()
                    for d in directors: motif_directors[m].add(d)
            elif n_base < 15000:
                n_base += 1
                for m in motifs: base_motifs[m] += 1

    print(f"\n[DEBUG] History Count: {len(history)} | Unique Matches: {n_liked}")
    
    # 3. SCORING
    results = []
    for term, c_l in liked_motifs.items():
        if c_l < MIN_FREQ: continue
        # Only keep phrases/words that appear across multiple directors
        if len(motif_directors.get(term, [])) < DIRECTOR_DIVERSITY: continue
        
        c_b = base_motifs.get(term, 0)
        score = math.log((c_l + ALPHA)/(n_liked - c_l + ALPHA)) - \
                math.log((c_b + ALPHA)/(n_base - c_b + ALPHA))
        
        results.append({
            "motif": term, 
            "score": round(score, 3), 
            "directors": len(motif_directors[term]),
            "liked_freq": c_l
        })

    if not results:
        print("Error: No patterns survived. Check history headers.")
        return

    df_out = pd.DataFrame(results).sort_values("score", ascending=False)
    
    # 4. SAFE SAVE (Solves the Permission Error)
    output_files = ["whitemask_fingerprint_latest.csv", f"whitemask_fingerprint_{timestamp}.csv"]
    for file in output_files:
        try:
            df_out.to_csv(file, index=False, encoding='utf-8-sig') # sig helps Excel handle symbols
            print(f"Success: {file}")
        except PermissionError:
            print(f"FAILED TO SAVE {file}: File is open in another program. Please close Excel and try again.")

if __name__ == "__main__":
    run()