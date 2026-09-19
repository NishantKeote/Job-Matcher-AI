"""Add targeted fallback links to the existing legacy CSV without changing row order."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import utility

path = ROOT / 'data' / 'job.csv'
df = pd.read_csv(path).fillna('')
if 'application_url' not in df.columns:
    df['application_url'] = ''
if 'source' not in df.columns:
    df['source'] = ''

mask = df['application_url'].astype(str).str.strip().eq('')
df.loc[mask, 'application_url'] = [
    utility.make_naukri_search_url(r.get('job_title', ''), r.get('company_name', ''), r.get('location', ''))
    for _, r in df.loc[mask].iterrows()
]
df.loc[mask, 'source'] = 'Naukri search fallback'
df.to_csv(path, index=False)
print(f'Updated {int(mask.sum())} legacy rows in {path}')
print('Embedding row order was preserved; no embedding regeneration is required for this link-only change.')
