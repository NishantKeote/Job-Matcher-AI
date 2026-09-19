"""Refresh the local job database from Adzuna.

Adzuna provides current job ads through its REST API. The API requires an
app_id and app_key. Put them in backend/.env:
    ADZUNA_APP_ID=...
    ADZUNA_APP_KEY=...

Example:
    python scripts/refresh_adzuna_jobs.py --country in --pages 3

After refreshing, regenerate embeddings:
    python scripts/generate_embeddings.py

The script stores the specific Adzuna listing URL returned by the API in
application_url, so the frontend can open the matching listing instead of a
broad Naukri search.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

DEFAULT_QUERIES = [
    "frontend developer",
    "react developer",
    "javascript developer",
    "software engineer",
    "full stack developer",
    "python developer",
    "backend developer",
    "data analyst",
    "machine learning engineer",
]


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch(country: str, query: str, page: int, app_id: str, app_key: str, results_per_page: int = 50):
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json",
        "sort_by": "date",
    }
    response = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
    response.raise_for_status()
    return response.json().get("results", [])


def normalize(job: dict) -> dict:
    loc = job.get("location") or {}
    company = job.get("company") or {}
    description = clean(job.get("description", ""))
    salary_min = job.get("salary_min", "")
    salary_max = job.get("salary_max", "")
    if salary_min or salary_max:
        salary = f"{salary_min}-{salary_max}"
    else:
        salary = ""

    return {
        "job_id": str(job.get("id", "")),
        "job_title": clean(job.get("title", "")),
        "company_name": clean(company.get("display_name", "")),
        "location": clean(loc.get("display_name", "")),
        "description": description,
        "skills": "",
        "experience": "",
        "ctc": salary,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "contract_type": clean(job.get("contract_type", "")),
        "employment_type": clean(job.get("contract_time", "")),
        "remote_type": "",
        "posted_at": clean(job.get("created", "")),
        "posted": clean(job.get("created", "")),
        "application_url": clean(job.get("redirect_url", "")),
        "source": "Adzuna",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="in", help="Adzuna country code; 'in' is India")
    parser.add_argument("--queries", nargs="+", default=DEFAULT_QUERIES)
    parser.add_argument("--pages", type=int, default=2)
    parser.add_argument("--results-per-page", type=int, default=50)
    args = parser.parse_args()

    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise SystemExit(
            "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY in backend/.env. "
            "Create an Adzuna developer account and add both values."
        )

    rows, seen = [], set()
    for query in args.queries:
        for page in range(1, args.pages + 1):
            results = fetch(args.country, query, page, app_id, app_key, args.results_per_page)
            if not results:
                break
            for job in results:
                row = normalize(job)
                key = row["job_id"] or (
                    row["job_title"].lower(), row["company_name"].lower(), row["location"].lower()
                )
                if key in seen or not row["job_title"]:
                    continue
                seen.add(key)
                rows.append(row)

    if not rows:
        raise SystemExit("No jobs returned. Check API credentials, country and queries.")

    df = pd.DataFrame(rows).drop_duplicates(
        subset=["job_title", "company_name", "location", "application_url"]
    )
    out = ROOT / "data" / "job.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} current Adzuna jobs to {out}")
    print("Next: python scripts/generate_embeddings.py")


if __name__ == "__main__":
    main()
