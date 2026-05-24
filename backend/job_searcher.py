import asyncio
import httpx
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalize_work_mode(raw: str) -> str:
    """Normalize work mode strings to Remote / Hybrid / Onsite."""
    raw = (raw or "").lower()
    if "remote" in raw:
        return "Remote"
    elif "hybrid" in raw:
        return "Hybrid"
    elif "onsite" in raw or "on-site" in raw or "in office" in raw or "in-office" in raw:
        return "Onsite"
    return "Unknown"


def matches_work_mode_filter(job_mode: str, filter_mode: str) -> bool:
    """Return True if job work mode matches the requested filter."""
    if not filter_mode or filter_mode.lower() == "any":
        return True
    return job_mode.lower() == filter_mode.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Source 1: RemoteOK (100% free, no key needed)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_remoteok(keywords: list, work_mode_filter: str, client: httpx.AsyncClient) -> list:
    """Fetch remote jobs from RemoteOK public API."""
    jobs = []
    try:
        response = await client.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "JobHunterAgent/1.0"},
            timeout=20,
        )
        if response.status_code != 200:
            return []
        data = response.json()
        # First item is metadata
        listings = [item for item in data if isinstance(item, dict) and "position" in item]

        kw_lower = [k.lower() for k in keywords]

        for job in listings[:80]:
            title = job.get("position", "")
            company = job.get("company", "")
            tags = " ".join(job.get("tags", [])).lower()
            description = job.get("description", "")

            # Basic keyword filter
            combined = (title + " " + tags + " " + description).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            work_mode = "Remote"
            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            jobs.append({
                "id": f"remoteok_{job.get('id', '')}",
                "title": title,
                "company": company,
                "location": job.get("location", "Remote / Worldwide"),
                "work_mode": work_mode,
                "description": description[:500] if description else "See full job listing.",
                "url": job.get("url", f"https://remoteok.com/remote-jobs/{job.get('slug', '')}"),
                "posted_at": job.get("date", ""),
                "salary": job.get("salary", ""),
                "source": "RemoteOK",
                "tags": job.get("tags", []),
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Source 2: Jobicy (free remote jobs, no key needed)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_jobicy(keywords: list, work_mode_filter: str, client: httpx.AsyncClient) -> list:
    """Fetch remote jobs from Jobicy public API."""
    jobs = []
    try:
        response = await client.get(
            "https://jobicy.com/api/v2/remote-jobs?count=50&geo=worldwide",
            headers={"User-Agent": "JobHunterAgent/1.0"},
            timeout=20,
        )
        if response.status_code != 200:
            return []
        data = response.json()
        listings = data.get("jobs", [])
        kw_lower = [k.lower() for k in keywords]

        for job in listings:
            title = job.get("jobTitle", "")
            company = job.get("companyName", "")
            description = job.get("jobDescription", "")
            combined = (title + " " + description).lower()

            if not any(kw in combined for kw in kw_lower):
                continue

            work_mode = "Remote"
            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            salary = ""
            if job.get("annualSalaryMin") and job.get("annualSalaryMax"):
                salary = f"${job['annualSalaryMin']:,} – ${job['annualSalaryMax']:,}/yr"

            jobs.append({
                "id": f"jobicy_{job.get('id', '')}",
                "title": title,
                "company": company,
                "location": job.get("jobGeo", "Remote / Worldwide"),
                "work_mode": work_mode,
                "description": description[:500] if description else "See full job listing.",
                "url": job.get("url", "https://jobicy.com"),
                "posted_at": job.get("pubDate", ""),
                "salary": salary,
                "source": "Jobicy",
                "tags": job.get("jobIndustry", []) if isinstance(job.get("jobIndustry"), list) else [],
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Source 3: Adzuna (free API, requires key — graceful skip if not set)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_adzuna(
    keywords: list,
    location: str,
    work_mode_filter: str,
    client: httpx.AsyncClient,
    app_id: str = "",
    app_key: str = "",
) -> list:
    """Fetch jobs from Adzuna API (requires free registration)."""
    if not app_id or not app_key:
        return []

    jobs = []
    query = " ".join(keywords[:3])
    country = "us"  # default

    try:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 30,
            "what": query,
            "where": location or "",
            "content-type": "application/json",
        }
        if work_mode_filter and work_mode_filter.lower() not in ("any", ""):
            if work_mode_filter.lower() == "remote":
                params["what"] = query + " remote"

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        response = await client.get(url, params=params, timeout=20)
        if response.status_code != 200:
            return []

        data = response.json()
        for job in data.get("results", []):
            raw_mode = "Remote" if "remote" in (job.get("title", "") + job.get("description", "")).lower() else "Onsite"
            work_mode = normalize_work_mode(raw_mode)
            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            jobs.append({
                "id": f"adzuna_{job.get('id', '')}",
                "title": job.get("title", ""),
                "company": job.get("company", {}).get("display_name", ""),
                "location": job.get("location", {}).get("display_name", location),
                "work_mode": work_mode,
                "description": job.get("description", "")[:500],
                "url": job.get("redirect_url", ""),
                "posted_at": job.get("created", ""),
                "salary": f"${job['salary_min']:,.0f} – ${job['salary_max']:,.0f}/yr"
                if job.get("salary_min") and job.get("salary_max") else "",
                "source": "Adzuna",
                "tags": job.get("category", {}).get("label", "").split(","),
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Source 4: JSearch via RapidAPI (free tier — covers Indeed, LinkedIn, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_jsearch(
    keywords: list,
    location: str,
    work_mode_filter: str,
    client: httpx.AsyncClient,
    rapidapi_key: str = "",
) -> list:
    """Fetch jobs from JSearch API on RapidAPI (free tier: 200 req/month)."""
    if not rapidapi_key:
        return []

    jobs = []
    query = " ".join(keywords[:3])
    if location:
        query += f" in {location}"
    if work_mode_filter and work_mode_filter.lower() not in ("any", ""):
        query += f" {work_mode_filter}"

    try:
        headers = {
            "X-RapidAPI-Key": rapidapi_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": query,
            "page": "1",
            "num_pages": "2",
            "date_posted": "month",
        }
        response = await client.get(
            "https://jsearch.p.rapidapi.com/search",
            headers=headers,
            params=params,
            timeout=25,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        for job in data.get("data", []):
            raw_mode = job.get("job_is_remote", False)
            if raw_mode:
                work_mode = "Remote"
            elif "hybrid" in (job.get("job_description", "") + job.get("job_title", "")).lower():
                work_mode = "Hybrid"
            else:
                work_mode = "Onsite"

            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            salary = ""
            if job.get("job_min_salary") and job.get("job_max_salary"):
                period = job.get("job_salary_period", "YEAR")
                salary = f"${job['job_min_salary']:,.0f} – ${job['job_max_salary']:,.0f}/{period[:2].lower()}"

            jobs.append({
                "id": f"jsearch_{job.get('job_id', '')}",
                "title": job.get("job_title", ""),
                "company": job.get("employer_name", ""),
                "location": job.get("job_city", "") + (", " + job.get("job_country", "") if job.get("job_country") else ""),
                "work_mode": work_mode,
                "description": job.get("job_description", "")[:500],
                "url": job.get("job_apply_link", job.get("job_google_link", "")),
                "posted_at": job.get("job_posted_at_datetime_utc", ""),
                "salary": salary,
                "source": "JSearch (LinkedIn/Indeed/Glassdoor)",
                "tags": job.get("job_required_skills", []) or [],
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Source 5: The Muse (free, no key needed)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_themuse(keywords: list, work_mode_filter: str, client: httpx.AsyncClient) -> list:
    """Fetch jobs from The Muse API (free, no key required)."""
    jobs = []
    try:
        query = " ".join(keywords[:2])
        params = {
            "page": 1,
            "descending": "true",
        }
        response = await client.get(
            f"https://www.themuse.com/api/public/jobs",
            params=params,
            headers={"User-Agent": "JobHunterAgent/1.0"},
            timeout=20,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        kw_lower = [k.lower() for k in keywords]

        for job in data.get("results", []):
            title = job.get("name", "")
            company = job.get("company", {}).get("name", "")
            description_html = ""
            if job.get("contents"):
                description_html = job["contents"][:500]

            combined = (title + " " + description_html).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            locations = job.get("locations", [])
            loc_str = ", ".join(l.get("name", "") for l in locations) if locations else "Not specified"

            raw_mode = "Remote" if any("remote" in l.get("name", "").lower() for l in locations) else "Onsite"
            work_mode = normalize_work_mode(raw_mode)

            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            jobs.append({
                "id": f"themuse_{job.get('id', '')}",
                "title": title,
                "company": company,
                "location": loc_str,
                "work_mode": work_mode,
                "description": description_html[:500],
                "url": job.get("refs", {}).get("landing_page", "https://www.themuse.com/jobs"),
                "posted_at": job.get("publication_date", ""),
                "salary": "",
                "source": "The Muse",
                "tags": [cat.get("name", "") for cat in job.get("categories", [])],
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Source 6: Arbeitnow (free — European + remote jobs, no key needed)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_arbeitnow(keywords: list, work_mode_filter: str, client: httpx.AsyncClient) -> list:
    """Fetch jobs from Arbeitnow free API."""
    jobs = []
    try:
        response = await client.get(
            "https://www.arbeitnow.com/api/job-board-api",
            headers={"User-Agent": "JobHunterAgent/1.0"},
            timeout=20,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        kw_lower = [k.lower() for k in keywords]

        for job in data.get("data", [])[:60]:
            title = job.get("title", "")
            company = job.get("company_name", "")
            description = job.get("description", "")

            combined = (title + " " + description).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            is_remote = job.get("remote", False)
            work_mode = "Remote" if is_remote else "Onsite"

            if not matches_work_mode_filter(work_mode, work_mode_filter):
                continue

            jobs.append({
                "id": f"arbeitnow_{job.get('slug', '')}",
                "title": title,
                "company": company,
                "location": job.get("location", "Germany / EU"),
                "work_mode": work_mode,
                "description": description[:500],
                "url": job.get("url", "https://www.arbeitnow.com"),
                "posted_at": job.get("created_at", ""),
                "salary": "",
                "source": "Arbeitnow",
                "tags": job.get("tags", []),
            })
    except Exception:
        pass
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ─────────────────────────────────────────────────────────────────────────────

async def search_all_sources(
    keywords: list,
    location: str,
    work_mode_filter: str,
    rapidapi_key: str = "",
    adzuna_app_id: str = "",
    adzuna_app_key: str = "",
) -> list:
    """
    Search all configured job sources in parallel and return aggregated results.
    Deduplicates by title+company.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [
            fetch_remoteok(keywords, work_mode_filter, client),
            fetch_jobicy(keywords, work_mode_filter, client),
            fetch_themuse(keywords, work_mode_filter, client),
            fetch_arbeitnow(keywords, work_mode_filter, client),
        ]

        # Optional premium sources
        if rapidapi_key:
            tasks.append(fetch_jsearch(keywords, location, work_mode_filter, client, rapidapi_key))
        if adzuna_app_id and adzuna_app_key:
            tasks.append(fetch_adzuna(keywords, location, work_mode_filter, client, adzuna_app_id, adzuna_app_key))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    # Filter by location if specified (fuzzy match)
    if location and location.strip():
        loc_lower = location.lower()
        location_filtered = []
        for job in all_jobs:
            job_loc = (job.get("location", "") + " " + job.get("work_mode", "")).lower()
            # Include job if location matches OR it's remote (remote is location-agnostic)
            if loc_lower in job_loc or job.get("work_mode", "").lower() == "remote":
                location_filtered.append(job)
        all_jobs = location_filtered

    # Deduplicate by normalized title+company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs
