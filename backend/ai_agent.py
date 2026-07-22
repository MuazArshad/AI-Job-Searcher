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
    Use Groq LLM to score and rank job listings against the resume.
    Returns jobs list with 'match_score', 'match_reason', and 'matching_skills' added.
    """
    if not jobs:
        return []

    # Prepare a compact resume summary for the prompt
    skills_list = resume_data.get('skills', [])
    resume_summary = f"""
Candidate Name: {resume_data.get('name', 'Professional')}
Summary: {resume_data.get('summary', 'N/A')}
Core Skills: {', '.join(skills_list[:25])}
Years of Experience: {resume_data.get('years_of_experience', 0)}
Target Roles: {', '.join(resume_data.get('target_roles', []))}
Education: {resume_data.get('education', 'N/A')}
Industries: {', '.join(resume_data.get('industries', []))}
""".strip()

    # Score top 40 jobs
    jobs_for_prompt = jobs[:40]
    jobs_text = ""
    for i, job in enumerate(jobs_for_prompt):
        desc = (job.get('description') or '').replace('\n', ' ')[:400]
        jobs_text += f"""
Job Index {i}:
  Title: {job.get('title', 'N/A')}
  Company: {job.get('company', 'N/A')}
  Location: {job.get('location', 'N/A')}
  Work Mode: {job.get('work_mode', 'N/A')}
  Source: {job.get('source', 'N/A')}
  Snippet: {desc}
"""

    prompt = f"""You are a top-tier recruitment AI & career strategist. Evaluate how well each job listing matches the candidate's profile.

CANDIDATE PROFILE:
{resume_summary}

JOB LISTINGS TO EVALUATE:
{jobs_text}

INSTRUCTIONS:
1. For each job (0 to {len(jobs_for_prompt)-1}), calculate a match score from 0 to 100 based on:
   - Skill overlap (tech stack & domain fit)
   - Role title relevance & seniority fit
   - Work mode / context compatibility
2. Provide a 1-sentence concise reason explaining the score.
3. List 2-4 key overlapping matching skills.

Return ONLY a valid JSON array of objects (no markdown wrapping, no code fences):
[
  {{"index": 0, "score": 92, "reason": "Exact fit for Python & FastAPI backend development with matching experience.", "matching_skills": ["Python", "FastAPI", "REST API"]}},
  ...
]
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        scores = json.loads(raw)

        score_map = {item["index"]: item for item in scores if isinstance(item, dict) and "index" in item}
        for i, job in enumerate(jobs_for_prompt):
            info = score_map.get(i, {})
            job["match_score"] = info.get("score", 60)
            job["match_reason"] = info.get("reason", "Good overall match for your professional background.")
            job["matching_skills"] = info.get("matching_skills", [])

        for job in jobs[40:]:
            job["match_score"] = 50
            job["match_reason"] = "Potential match based on keywords."
            job["matching_skills"] = []

        return sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)

    except Exception as e:
        print(f"[AI Agent] Match ranking fallback: {e}")
        # Fallback scoring
        candidate_skills = [s.lower() for s in skills_list]
        for job in jobs:
            text = (job.get("title", "") + " " + job.get("description", "")).lower()
            matched = [s for s in skills_list if s.lower() in text]
            score = min(95, 50 + len(matched) * 10) if matched else 50
            job["match_score"] = job.get("match_score", score)
            job["match_reason"] = job.get("match_reason", f"Matches skills: {', '.join(matched[:3])}" if matched else "Relevant job posting.")
            job["matching_skills"] = job.get("matching_skills", matched[:4])
        return sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)


def generate_search_keywords(resume_data: dict) -> list:
    """Generate clean, high-precision job search query terms from resume analysis."""
    target_roles = resume_data.get("target_roles", [])
    skills = resume_data.get("skills", [])
    
    clean_queries = []
    
    # Primary search query: combinations of target roles or main titles
    for role in target_roles[:2]:
        if role and len(role.strip()) > 2:
            clean_queries.append(role.strip())
            
    # If no target roles, build from top skills
    if not clean_queries and skills:
        top_skill = skills[0].strip()
        clean_queries.append(f"{top_skill} Developer")
        clean_queries.append(f"{top_skill} Engineer")
        
    if not clean_queries:
        clean_queries = ["Software Engineer"]
        
    return clean_queries
