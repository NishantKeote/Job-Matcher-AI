# AI Based Job Recommendation System — Web Version v3

A React/Vite + FastAPI resume-to-job recommendation system.

## What this version does

- Extracts text from an uploaded resume PDF.
- Uses Gemini 3.6 Flash to extract concise candidate keywords.
- Uses the bundled `all-MiniLM-L6-v2` Sentence Transformer for semantic matching.
- Combines semantic similarity, skill overlap, experience compatibility and posting freshness.
- **Live mode:** when Adzuna credentials are configured, fetches fresh job ads for each resume request and uses the specific listing URL returned by the provider.
- **Local fallback:** if live credentials are absent, uses the bundled `data/job.csv` snapshot and its targeted legacy search fallbacks.
- React frontend displays the recommendations and opens the returned job listing URL.

## Live job mode — recommended

Adzuna requires an `app_id` and `app_key`. Register through the Adzuna developer portal, then create `backend/.env` from `backend/.env.example`:

```env
GOOGLE_API_KEY=your_gemini_api_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
ADZUNA_COUNTRY=in
ADZUNA_RESULTS_PER_PAGE=30
LIVE_JOBS=auto
```

With `LIVE_JOBS=auto`, the backend automatically switches to live jobs when both Adzuna credentials exist. Set `LIVE_JOBS=false` to force the bundled local dataset.

## Run backend

```bash
cd backend
python -m venv venv
# Windows PowerShell:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to test the API.

## Run frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Then:

```bash
npm run dev
```

## Static snapshot mode

If you prefer a local job snapshot, use the refresh script:

```bash
cd backend
python scripts/refresh_adzuna_jobs.py --country in --pages 3
python scripts/generate_embeddings.py
```

The refresh script stores descriptions, posting timestamps and the specific listing URL returned by Adzuna in `data/job.csv`.

## Important

Do not commit `backend/.env` or expose API keys. The bundled dataset is a fallback snapshot; it should not be described as a live job feed unless live mode is enabled.
