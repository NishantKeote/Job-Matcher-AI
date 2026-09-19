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