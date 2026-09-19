"""Regenerate job_embeddings.npy after changing data/job.csv.

Run from the backend root:
    python scripts/generate_embeddings.py
"""
from pathlib import Path
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import utility

model = SentenceTransformer(str(ROOT / "models" / "sentenceTransformer"))
df = utility.load_job_data(str(ROOT / "data" / "job.csv"))
texts = [utility.build_job_text(row) for _, row in df.iterrows()]
embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
out = ROOT / "data" / "job_embeddings.npy"
np.save(out, embeddings)
print(f"Saved {len(embeddings)} embeddings with shape {embeddings.shape} -> {out}")
