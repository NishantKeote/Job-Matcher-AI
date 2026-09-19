# Backend — AI Job Recommendation API

## Modes

### Live jobs (recommended for the deployed project)

The API can fetch fresh job advertisements from Adzuna for each uploaded resume. Put these in `backend/.env`:

```env
GOOGLE_API_KEY=...
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
ADZUNA_COUNTRY=in
ADZUNA_RESULTS_PER_PAGE=30
LIVE_JOBS=auto
```

With `LIVE_JOBS=auto`, live mode is enabled automatically when both Adzuna credentials are present. The API uses the specific listing URL returned by Adzuna instead of inventing a Naukri search URL.

### Local fallback

If Adzuna credentials are not configured, the API falls back to `data/job.csv` and its legacy search URLs. Set `LIVE_JOBS=false` to force local mode.

## Refresh the local dataset

If you want a static snapshot instead of fetching jobs per resume:

```bash
python scripts/refresh_adzuna_jobs.py --country in --pages 3
python scripts/generate_embeddings.py
```

The refresh script stores job descriptions, timestamps, company/location fields and the listing URL returned by Adzuna.

## Run

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```
