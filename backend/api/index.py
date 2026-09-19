from __future__ import annotations

import os
import re
from pathlib import Path
from datetime import datetime, timezone
import time

os.environ["TRANSFORMERS_NO_TF"] = "1"

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import fitz
from google import genai
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
import requests
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import utility

app = FastAPI(title="AI Job Recommendation API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv(ROOT / ".env")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

model_path = ROOT / "models" / "sentenceTransformer"
model = SentenceTransformer(str(model_path))

jobs_path = ROOT / "data" / "job.csv"
embeddings_path = ROOT / "data" / "job_embeddings.npy"
jobs = utility.load_job_data(str(jobs_path))
job_embeddings = np.load(str(embeddings_path))

if len(jobs) != len(job_embeddings):
    raise RuntimeError(
        f"Job data ({len(jobs)}) and embeddings ({len(job_embeddings)}) have different row counts. "
        "Run scripts/generate_embeddings.py after changing the dataset."
    )


def extract_text_from_pdf(pdf_content: bytes) -> str:
    try:
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
        if not text.strip():
            raise HTTPException(status_code=400, detail="The PDF contains no extractable text.")
        return text.strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting PDF text: {str(e)}")


def summarize_and_extract_keywords(resume_text: str) -> str:
    prompt = f"""
You are a resume analyzer for a job recommendation system.
Extract the candidate's most relevant skills, technologies, role keywords, experience level,
and career focus. Prefer concrete technologies and job-role terms over generic words.
Return a concise comma-separated list of up to 20 keywords.

Resume:
{resume_text}
"""

    # Gemini can temporarily return 503 during periods of high demand.
    # Retry briefly, then fall back to local keyword extraction so that
    # live-job recommendations can still work without Gemini.
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
    ]

    last_error = None

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                result = getattr(response, "text", None)
                if result and result.strip():
                    print(f"Gemini success using {model_name}")
                    return result.strip()

            except Exception as e:
                last_error = e
                print(
                    f"Gemini failed using {model_name} "
                    f"(attempt {attempt + 1}/2): {e}"
                )

                # A short delay helps with temporary 503/high-demand errors.
                if attempt == 0:
                    time.sleep(1.5)

    # Local fallback: keep the recommendation system usable when Gemini
    # is temporarily unavailable.
    fallback_terms = [
        "python", "java", "c++", "c", "javascript", "typescript",
        "html", "css", "react", "react.js", "redux", "node.js", "node",
        "express", "fastapi", "django", "flask", "mongodb", "mysql",
        "postgresql", "sql", "git", "github", "docker", "aws",
        "machine learning", "deep learning", "artificial intelligence",
        "tensorflow", "pytorch", "scikit-learn", "nlp", "pandas",
        "numpy", "opencv", "streamlit", "vite", "tailwind",
        "frontend", "front end", "backend", "back end", "full stack",
        "software developer", "software engineer", "web developer",
        "data analyst", "data scientist", "aiml"
    ]

    resume_lower = resume_text.lower()
    found = []

    for term in fallback_terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, resume_lower):
            found.append(term)

    # Add useful role terms when they are explicitly present in the resume.
    role_terms = [
        "frontend developer", "backend developer", "full stack developer",
        "software developer", "software engineer", "web developer",
        "machine learning engineer", "data analyst", "data scientist"
    ]
    for term in role_terms:
        if term in resume_lower and term not in found:
            found.append(term)

    if found:
        fallback = ", ".join(found[:20])
        print(f"Using local resume-keyword fallback: {fallback}")
        return fallback

    # Last-resort fallback: use the first meaningful words from the resume.
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", resume_text)
    generic = {
        "resume", "curriculum", "vitae", "email", "phone", "address",
        "linkedin", "github", "education", "experience", "project",
        "projects", "skills", "objective", "summary", "college",
        "university", "student"
    }
    unique_words = []
    seen_words = set()

    for word in words:
        key = word.lower()
        if key not in generic and key not in seen_words:
            seen_words.add(key)
            unique_words.append(word)

    if unique_words:
        fallback = ", ".join(unique_words[:20])
        print(f"Using generic local keyword fallback: {fallback}")
        return fallback

    if last_error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini is temporarily unavailable and no usable resume "
                f"keywords could be extracted locally. Last Gemini error: {last_error}"
            ),
        )

    raise HTTPException(
        status_code=503,
        detail="Could not extract usable keywords from the resume."
    )



def cosine_similarity_manual(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    dot = np.dot(b, a)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b, axis=1)
    return dot / (norm_a * norm_b + 1e-8)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", str(text).lower()).strip()


def _experience_range(value: str):
    text = _norm(value)
    if not text:
        return None, None
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[1]


def extract_experience_requirement(text: str) -> str:
    """Extract the strongest explicit experience requirement from a job."""
    text = str(text or "")
    if not text.strip():
        return ""

    normalized = (
        text.replace("–", "-")
            .replace("—", "-")
            .replace("−", "-")
            .replace("’", "'")
    )
    lower = normalized.lower()

    # Explicit numeric requirements. These are checked BEFORE title signals
    # so "Jr. Data Scientist (5 yrs) Experience: 5 Years" is not misclassified.
    patterns = [
        (r"\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}-{m.group(2)} years"),
        (r"\b(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}+ years"),
        (r"\b(?:at\s+least|minimum(?:\s+of)?|minimum)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}+ years"),
        (r"\bexperience\s*[:\-]?\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}+ years"),
        (r"\b(?:roughly|around|about|with|requires?|requiring|having|of)\s+"
         r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}+ years"),
        (r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b",
         lambda m: f"{m.group(1)}+ years"),
        # Common malformed/unstyled job text: "Experience - 2 3 years"
        (r"\bexperience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}-{m.group(2)} years"),
        # Title-style "(5 yrs)" / "5 yrs" when no stronger phrase exists.
        (r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
         lambda m: f"{m.group(1)}+ years"),
    ]

    for pattern, formatter in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return formatter(match)

    # Explicit entry-level signals only after numeric requirements.
    if re.search(
        r"\b(fresher|fresh graduate|entry[- ]level|early[- ]career|"
        r"trainee|graduate|new grad|0[- ]?2 years?)\b",
        lower,
    ):
        return "0-2 years"

    # Numbered engineering levels.
    if re.search(r"\b(?:software engineer|sde|developer)\s*(?:i|1)\b", lower):
        return "0-2 years"
    if re.search(r"\b(?:software engineer|sde|developer)\s*(?:ii|2)\b", lower):
        return "2-4 years"
    if re.search(r"\b(?:software engineer|sde|developer)\s*(?:iii|3)\b", lower):
        return "4+ years"

    # Seniority heuristics should be based on the job title, not arbitrary
    # mentions in the description (for example "junior / mid / senior").
    title_text = lower.split("\n", 1)[0]
    if re.search(r"\b(principal|staff|architect|director|manager)\b", title_text):
        return "5+ years"
    if re.search(r"\b(senior|sr\.?|lead)\b", title_text):
        return "3+ years"
    if re.search(r"\b(junior|jr\.?)\b", title_text):
        return "0-2 years"

    return ""


def experience_score(requirement: str, candidate_level: str) -> float:
    lo, hi = _experience_range(requirement)

    if lo is None:
        # Unknown experience should be neutral, but not better than a
        # clearly entry-level match.
        return 0.45

    candidate_level = (candidate_level or "").lower()
    candidate_years = 0 if any(
        word in candidate_level for word in ("fresh", "entry", "graduate")
    ) else 2

    if candidate_years == 0:
        if lo <= 0 and (hi is None or hi <= 2):
            return 1.0
        if lo <= 1 and (hi is None or hi <= 2):
            return 0.95
        if lo == 2 and (hi is None or hi <= 3):
            return 0.75
        if lo == 3 and (hi is None or hi <= 4):
            return 0.30
        if lo >= 4:
            return 0.05

    if lo <= candidate_years <= (hi if hi is not None else lo):
        return 1.0

    if candidate_years < lo:
        gap = lo - candidate_years
        return max(0.0, 1.0 - 0.35 * gap)

    return 0.75


def token_set(text: str):
    normalized = _norm(text)
    tokens = {
        x for x in re.findall(r"[a-z][a-z0-9+#.\-]{0,}", normalized)
        if len(x) > 1
    }

    # Useful aliases that frequently appear in resumes/jobs.
    aliases = {
        "react.js": "react",
        "reactjs": "react",
        "node.js": "node",
        "nodejs": "node",
        "javascript": "js",
        "typescript": "ts",
        "html5": "html",
        "css3": "css",
        "c++": "cpp",
        "fastapi": "fastapi",
        "rest": "api",
        "restful": "api",
    }

    expanded = set(tokens)
    for token in list(tokens):
        if token in aliases:
            expanded.add(aliases[token])

    return expanded


def skill_score(resume_keywords: str, row) -> float:
    """Score concrete technology/skill overlap, with extra weight for title/skills."""
    resume = token_set(resume_keywords)
    if not resume:
        return 0.0

    title = token_set(str(row.get("job_title", "")))
    skills = token_set(str(row.get("skills", "")))
    description = token_set(str(row.get("description", "")))

    # Ignore generic role words when measuring technical-skill overlap.
    generic = {
        "developer", "engineer", "software", "web", "frontend", "backend",
        "front", "end", "full", "stack", "entry", "level", "junior",
        "senior", "remote", "india", "work", "years", "experience"
    }

    tech_candidate = {x for x in resume if x not in generic}
    if not tech_candidate:
        return 0.0

    strong = (title | skills) & tech_candidate
    desc = description & tech_candidate

    # A match in the title/skills is much stronger than a generic mention
    # buried in the description.
    strong_ratio = len(strong) / max(1, min(6, len(tech_candidate)))
    desc_ratio = len(desc) / max(1, min(10, len(tech_candidate)))

    score = 0.75 * min(1.0, strong_ratio) + 0.25 * min(1.0, desc_ratio)

    # Extra boost for the most important frontend technologies.
    frontend_tech = {"react", "js", "javascript", "html", "css", "vite"}
    if any(x in title for x in ("frontend", "front end", "react")):
        frontend_matches = len(frontend_tech & resume & (title | skills | description))
        if frontend_matches:
            score += min(0.20, 0.05 * frontend_matches)

    return min(1.0, score)


def role_fit_score(resume_keywords: str, row) -> float:
    """Estimate broad role-family compatibility from candidate keywords and job title."""
    candidate = _norm(resume_keywords)
    title = _norm(str(row.get("job_title", "")))
    description = _norm(str(row.get("description", "")))

    # Candidate's explicit role signals.
    frontend = any(x in candidate for x in (
        "frontend developer", "front end developer", "web developer",
        "react", "html", "css", "javascript"
    ))
    backend = any(x in candidate for x in (
        "backend developer", "back end developer", "fastapi", "django", "flask"
    ))
    fullstack = any(x in candidate for x in (
        "full stack", "fullstack"
    ))

    if not (frontend or backend or fullstack):
        return 0.5

    is_frontend = any(x in title for x in ("frontend", "front end", "react developer", "ui developer", "web developer"))
    is_backend = any(x in title for x in ("backend", "back end", "django developer", "python developer", "api developer"))
    is_fullstack = any(x in title for x in ("full stack", "fullstack"))
    is_data = any(x in title for x in ("data scientist", "data analyst", "ml engineer", "machine learning engineer"))

    if is_data and not ("data" in candidate or "machine learning" in candidate or "aiml" in candidate):
        return 0.3

    if frontend:
        if is_frontend:
            return 1.0
        if is_fullstack:
            return 0.78
        if is_backend:
            return 0.40
        if "software engineer" in title or "software developer" in title:
            return 0.70

    if backend:
        if is_backend:
            return 1.0
        if is_fullstack:
            return 0.82
        if is_frontend:
            return 0.45

    if fullstack and is_fullstack:
        return 1.0

    # If the title is generic but the description explicitly mentions a
    # candidate's main role family, give it a moderate score.
    if frontend and any(x in description for x in ("frontend", "front end", "react")):
        return 0.72
    if backend and any(x in description for x in ("backend", "back end", "fastapi", "django", "flask")):
        return 0.72

    return 0.5


def freshness_score(row) -> float:
    # Prefer explicit posted_at/created timestamps in refreshed datasets.
    raw = str(row.get("posted_at", row.get("created", ""))).strip()
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            age = max(0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days)
            return float(np.exp(-age / 21.0))
        except ValueError:
            pass

    # Legacy dataset only has relative text such as "3 days ago".
    text = str(row.get("posted", "")).lower()
    m = re.search(r"(\d+)\s+(day|week|month)", text)
    if not m:
        return 0.25
    n = int(m.group(1))
    unit = m.group(2)
    days = n if unit == "day" else n * 7 if unit == "week" else n * 30
    return float(np.exp(-days / 21.0))


def build_job_response(row, index: int, similarity: float, skills: float, exp: float, freshness: float, role_fit: float):
    title = str(row.get("job_title", "Recommended role"))
    company = str(row.get("company_name", ""))
    direct = bool(row.get("has_direct_application_url", False))
    return {
        "job_id": str(row.get("job_id", "")) or int(index),
        "title": title[:200],
        "company": company[:200],
        "location": str(row.get("location", ""))[:200],
        "experience": str(row.get("experience", ""))[:100],
        "salary": str(row.get("ctc", row.get("salary", "")))[:120],
        "posted": str(row.get("posted", row.get("posted_at", "")))[:120],
        "description": str(row.get("description", ""))[:500],
        "similarity_score": round(float(similarity), 4),
        "skill_score": round(float(skills), 4),
        "experience_score": round(float(exp), 4),
        "freshness_score": round(float(freshness), 4),
        "match_score": round(float(0.40 * similarity + 0.30 * skills + 0.15 * exp + 0.05 * freshness + 0.10 * role_fit), 4),
        "listing_url": str(
            row.get("application_url_resolved")
            or row.get("application_url")
            or ""
        ),
        "application_url": str(
            row.get("application_url_resolved")
            or row.get("application_url")
            or ""
        ),
        "is_direct_application_url": False if str(row.get("source", "")).lower() == "adzuna" else direct,
        "source": str(row.get("source", "Unknown")) or "Unknown",
    }


@app.get("/")
def health():
    return {"status": "ok", "jobs_loaded": int(len(jobs))}



def fetch_live_adzuna_jobs(resume_keywords: str) -> pd.DataFrame:
    """Fetch a fresh candidate pool from Adzuna for the current resume."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return pd.DataFrame()

    country = os.getenv("ADZUNA_COUNTRY", "in")
    per_page = max(10, min(int(os.getenv("ADZUNA_RESULTS_PER_PAGE", "30")), 50))
    terms = [x.strip() for x in resume_keywords.split(",") if x.strip()]
    queries = []
    if terms:
        queries.append(" ".join(terms[:7]))
    lowered = resume_keywords.lower()
    if any(x in lowered for x in ["frontend", "front end", "react", "javascript", "html", "css"]):
        queries.append("frontend developer")
    if any(x in lowered for x in ["python", "fastapi", "django", "flask"]):
        queries.append("python developer")
    if not queries:
        queries.append("software engineer")

    rows, seen = [], set()
    for query in queries[:3]:
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": per_page,
            "what": query,
            "content-type": "application/json",
            "sort_by": "date",
        }
        response = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=20)
        response.raise_for_status()
        for job in response.json().get("results", []):
            loc = job.get("location") or {}
            company = job.get("company") or {}
            job_id = str(job.get("id", ""))
            key = job_id or (str(job.get("title", "")).lower(), str(company.get("display_name", "")).lower(), str(loc.get("display_name", "")).lower())
            if key in seen or not job.get("title"):
                continue
            seen.add(key)
            salary_min = job.get("salary_min", "")
            salary_max = job.get("salary_max", "")
            rows.append({
                "job_id": job_id,
                "job_title": str(job.get("title", "")),
                "company_name": str(company.get("display_name", "")),
                "location": str(loc.get("display_name", "")),
                "description": str(job.get("description", "")),
                "skills": "",
                "experience": extract_experience_requirement(
                    f"{job.get('title', '')} {job.get('description', '')}"
                ),
                "ctc": f"{salary_min}-{salary_max}" if salary_min or salary_max else "",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "contract_type": str(job.get("contract_type", "")),
                "employment_type": str(job.get("contract_time", "")),
                "remote_type": "",
                "posted_at": str(job.get("created", "")),
                "posted": str(job.get("created", "")),
                "application_url": str(job.get("redirect_url", "")),
                "source": "Adzuna",
            })
    return utility.load_job_data_from_dataframe(pd.DataFrame(rows)) if rows else pd.DataFrame()


def rank_jobs(job_df: pd.DataFrame, resume_embedding, resume_summary: str, experience: str):
    texts = [utility.build_job_text(row) for _, row in job_df.iterrows()]
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
    similarities = cosine_similarity_manual(resume_embedding, embeddings)
    scored = []
    for pos, (_, row) in enumerate(job_df.iterrows()):
        sem = float(similarities[pos])
        skills = skill_score(resume_summary, row)
        exp = experience_score(str(row.get("experience", "")), experience)
        fresh = freshness_score(row)
        role_fit = role_fit_score(resume_summary, row)

        # Fresher-specific safety filter: roles explicitly requiring 4+ years
        # should not outrank genuinely entry-level roles merely because of
        # generic semantic similarity.
        final = 0.40 * sem + 0.30 * skills + 0.15 * exp + 0.05 * fresh + 0.10 * role_fit

        # Strong penalty for clear senior requirements when candidate is fresher.
        if "fresh" in (experience or "").lower() and str(row.get("experience", "")).strip():
            lo, _ = _experience_range(str(row.get("experience", "")))
            if lo is not None and lo >= 4:
                final *= 0.55

        scored.append((final, pos, sem, skills, exp, fresh, role_fit))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [
        build_job_response(job_df.iloc[pos], int(pos), sem, skills, exp, fresh, role_fit)
        for _, pos, sem, skills, exp, fresh, role_fit in scored[:10]
    ]

@app.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    experience: str = Form("fresher"),
):
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        pdf_content = await file.read()
        resume_text = extract_text_from_pdf(pdf_content)
        resume_summary = summarize_and_extract_keywords(resume_text)
        resume_embedding = model.encode(resume_summary, convert_to_numpy=True, normalize_embeddings=True)

        mode = os.getenv("LIVE_JOBS", "auto").lower()
        live_enabled = mode == "true" or (mode == "auto" and os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))

        if live_enabled:
            try:
                live_jobs = fetch_live_adzuna_jobs(resume_summary)
            except requests.RequestException as e:
                raise HTTPException(status_code=502, detail=f"Live job provider request failed: {str(e)}")
            if live_jobs.empty:
                raise HTTPException(status_code=502, detail="Live job mode is enabled, but no current jobs were returned. Check Adzuna credentials and queries.")
            job_matches = rank_jobs(live_jobs, resume_embedding, resume_summary, experience)
            return {"keywords": resume_summary, "jobs": job_matches, "live_jobs": True, "job_count": int(len(live_jobs))}

        job_matches = rank_jobs(jobs, resume_embedding, resume_summary, experience)
        return {"keywords": resume_summary, "jobs": job_matches, "live_jobs": False, "job_count": int(len(jobs))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
