from __future__ import annotations

import re
from urllib.parse import quote_plus
from pathlib import Path

import pandas as pd


def load_resume_data(resume_path):
    df = pd.read_csv(resume_path)
    return df['Resume'].dropna().tolist()


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def make_naukri_search_url(title: str, company: str = "", location: str = "") -> str:
    """Build a targeted Naukri search URL when a direct listing URL is unavailable."""
    title = _clean(title)
    company = _clean(company)
    location = _clean(location)
    query_parts = [p for p in (title, company, location) if p]
    query = quote_plus(" ".join(query_parts))
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "jobs"
    return f"https://www.naukri.com/{slug}-jobs?k={query}"


def build_job_text(row) -> str:
    """Text used for embeddings. Works with both the legacy and refreshed schemas."""
    parts = [
        f"Job title: {_clean(row.get('job_title', row.get('title', '')))}",
        f"Company: {_clean(row.get('company_name', row.get('company', '')))}",
        f"Location: {_clean(row.get('location', ''))}",
        f"Experience: {_clean(row.get('experience', ''))}",
        f"Salary: {_clean(row.get('ctc', ''))}",
        f"Employment type: {_clean(row.get('employment_type', row.get('contract_type', '')))}",
        f"Work mode: {_clean(row.get('remote_type', row.get('work_mode', '')))}",
        f"Skills: {_clean(row.get('skills', ''))}",
        f"Description: {_clean(row.get('description', ''))}",
    ]
    return " | ".join(p for p in parts if not p.endswith(": "))



def load_job_data_from_dataframe(df):
    """Apply the same derived URL fields to an in-memory job dataframe."""
    df = df.copy().fillna("")
    if 'job_title' not in df.columns and 'title' in df.columns:
        df['job_title'] = df['title']
    if 'company_name' not in df.columns and 'company' in df.columns:
        df['company_name'] = df['company']
    if 'application_url' not in df.columns:
        df['application_url'] = ""
    if 'source' not in df.columns:
        df['source'] = ""
    resolved, direct = [], []
    for _, row in df.iterrows():
        url = _clean(row.get('application_url', ''))
        source = _clean(row.get('source', ''))
        is_fallback = source.lower() in {'naukri search fallback', 'naukri search'}
        resolved.append(url or make_naukri_search_url(row.get('job_title', ''), row.get('company_name', ''), row.get('location', '')))
        direct.append(bool(url) and not is_fallback)
    df['application_url_resolved'] = resolved
    df['has_direct_application_url'] = direct
    return df

def load_job_data(job_path):
    """Load the job table and add safe derived fields used by the API/frontend."""
    return load_job_data_from_dataframe(pd.read_csv(job_path))
def load_job_data_from_dataframe(df):
    """Normalize live job data using the same schema as CSV jobs."""
    df = df.copy().fillna("")

    if "job_title" not in df.columns and "title" in df.columns:
        df["job_title"] = df["title"]

    if "company_name" not in df.columns and "company" in df.columns:
        df["company_name"] = df["company"]

    if "application_url" not in df.columns:
        df["application_url"] = ""

    if "source" not in df.columns:
        df["source"] = ""

    fallback_urls = []
    direct_flags = []

    for _, row in df.iterrows():
        url = _clean(row.get("application_url", ""))
        source = _clean(row.get("source", ""))

        is_fallback = source.lower() in {
            "naukri search fallback",
            "naukri search"
        }

        fallback_urls.append(
            url or make_naukri_search_url(
                row.get("job_title", ""),
                row.get("company_name", ""),
                row.get("location", "")
            )
        )

        direct_flags.append(
            bool(url) and not is_fallback
        )

    df["application_url_resolved"] = fallback_urls
    df["has_direct_application_url"] = direct_flags

    return df