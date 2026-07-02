import streamlit as st
import json
import sys
sys.path.append('.')
from utils.honeypot import get_honeypot_multiplier
from utils.scorer import compute_final_score
from utils.reasoning import generate_reasoning
import pandas as pd

st.title("TalentLens Ranker")

uploaded_file = st.file_uploader("Upload JSONL file", type="jsonl")

if uploaded_file:
    candidates = []
    for line in uploaded_file.read().decode().splitlines():
        if line.strip():
            candidates.append(json.loads(line))
    
    st.write(f"Loaded {len(candidates)} candidates")
    
    if st.button("Rank"):
        results = []
        bar = st.progress(0)
        for i, c in enumerate(candidates):
            mult = get_honeypot_multiplier(c)
            score, dims = compute_final_score(c, mult)
            results.append({"id": c["candidate_id"], "score": score, "dims": dims, "c": c})
            bar.progress((i+1)/len(candidates))
        
        results.sort(key=lambda x: (-x["score"], x["id"]))
        
        rows = []
        for i, r in enumerate(results[:100]):
            reasoning = generate_reasoning(r["c"], i+1, r["score"], r["dims"])
            rows.append({"candidate_id": r["id"], "rank": i+1, "score": round(r["score"],4), "reasoning": reasoning})
        
        df = pd.DataFrame(rows)
        st.dataframe(df)
        
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "submission.csv", "text/csv")