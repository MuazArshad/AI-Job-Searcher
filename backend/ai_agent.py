import json
import re
import groq
from config import GROQ_API_KEY

# Configure Groq
client = groq.Groq(api_key=GROQ_API_KEY)


def analyze_resume(resume_text: str) -> dict:
    """
    Use Gemini to extract structured information from resume text.
    Returns a dict with skills, experience, target_roles, education, summary.
    """
    prompt = f"""You are an expert resume analyzer. Analyze the following resume and extract key information.

Resume Text:
---
{resume_text[:8000]}
---

Return a JSON object (no markdown, no code fences, pure JSON) with these exact fields:
{{
  "name": "candidate's full name or 'Professional'",
  "summary": "2-3 sentence professional summary of this candidate",
  "skills": ["skill1", "skill2", ...],
  "years_of_experience": number or 0,
  "target_roles": ["role1", "role2", ...],
  "education": "highest education level and field",
  "industries": ["industry1", ...],
  "languages": ["English", ...],
  "key_highlights": ["highlight1", "highlight2", "highlight3"]
}}

Be concise and extract only what is clearly stated in the resume.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        # Remove markdown fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return basic structure
        return {
            "name": "Professional",
            "summary": "Experienced professional seeking new opportunities.",
            "skills": [],
            "years_of_experience": 0,
            "target_roles": ["Software Engineer"],
            "education": "Not specified",
            "industries": [],
            "languages": ["English"],
            "key_highlights": []
        }
    except Exception as e:
        raise RuntimeError(f"Gemini resume analysis failed: {e}")


def rank_jobs(resume_data: dict, jobs: list) -> list:
    """
    Use Gemini to score and rank job listings against the resume.
    Returns jobs list with 'match_score' and 'match_reason' added.
    """
    if not jobs:
        return []

    # Prepare a compact resume summary for the prompt
    resume_summary = f"""
Name: {resume_data.get('name', 'N/A')}
Skills: {', '.join(resume_data.get('skills', [])[:20])}
Years of Experience: {resume_data.get('years_of_experience', 0)}
Target Roles: {', '.join(resume_data.get('target_roles', []))}
Education: {resume_data.get('education', 'N/A')}
Industries: {', '.join(resume_data.get('industries', []))}
""".strip()

    # Prepare jobs list (limit to 30 for prompt efficiency)
    jobs_for_prompt = jobs[:30]
    jobs_text = ""
    for i, job in enumerate(jobs_for_prompt):
        jobs_text += f"""
Job {i}:
  Title: {job.get('title', 'N/A')}
  Company: {job.get('company', 'N/A')}
  Location: {job.get('location', 'N/A')}
  Type: {job.get('work_mode', 'N/A')}
  Description: {job.get('description', '')[:300]}
"""

    prompt = f"""You are an expert career coach and job matcher. Score each job listing based on how well it matches the candidate's resume.

CANDIDATE PROFILE:
{resume_summary}

JOB LISTINGS:
{jobs_text}

For each job (0 to {len(jobs_for_prompt)-1}), provide a match score from 0-100 and a brief reason (1 sentence).

Return ONLY a JSON array (no markdown, no code fences) like:
[
  {{"index": 0, "score": 85, "reason": "Strong match for Python skills and backend experience."}},
  {{"index": 1, "score": 60, "reason": "Partial match, requires Java which candidate lacks."}},
  ...
]

Score all {len(jobs_for_prompt)} jobs. Higher score = better match.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        scores = json.loads(raw)

        # Map scores back to jobs
        score_map = {item["index"]: item for item in scores}
        for i, job in enumerate(jobs_for_prompt):
            info = score_map.get(i, {})
            job["match_score"] = info.get("score", 50)
            job["match_reason"] = info.get("reason", "Potential match based on profile.")

        # For any jobs beyond the 30 limit, assign a default score
        for job in jobs[30:]:
            job["match_score"] = 45
            job["match_reason"] = "Not individually scored — potential match."

        # Sort by score descending
        return sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)

    except Exception:
        # Fallback: just return jobs with default scores
        for job in jobs:
            if "match_score" not in job:
                job["match_score"] = 50
                job["match_reason"] = "Potential match based on your profile."
        return jobs


def generate_search_keywords(resume_data: dict) -> list:
    """Generate optimized job search keywords from resume analysis."""
    keywords = []

    # Add target roles
    keywords.extend(resume_data.get("target_roles", [])[:3])

    # Add top skills
    skills = resume_data.get("skills", [])
    keywords.extend(skills[:5])

    # Deduplicate and clean
    seen = set()
    clean = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower not in seen and kw_lower:
            seen.add(kw_lower)
            clean.append(kw.strip())

    return clean[:8] if clean else ["Software Engineer"]
