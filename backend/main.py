import os
import sys

# Allow imports from this directory
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

from config import GROQ_API_KEY
from resume_parser import parse_resume
from ai_agent import analyze_resume, rank_jobs, generate_search_keywords
from job_searcher import search_all_sources

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Job Hunting Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files at root so relative paths (styles.css, app.js) work
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/styles.css", include_in_schema=False)
async def serve_css():
    css_path = os.path.join(FRONTEND_DIR, "styles.css")
    return FileResponse(css_path, media_type="text/css", headers={"Cache-Control": "no-cache"})

@app.get("/app.js", include_in_schema=False)
async def serve_js():
    js_path = os.path.join(FRONTEND_DIR, "app.js")
    return FileResponse(js_path, media_type="application/javascript", headers={"Cache-Control": "no-cache"})



# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    resume_data: dict
    custom_query: Optional[str] = ""
    location: Optional[str] = ""
    work_mode: Optional[str] = "Any"   # Any | Remote | Hybrid | Onsite
    rapidapi_key: Optional[str] = ""
    adzuna_app_id: Optional[str] = ""
    adzuna_app_key: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI Job Hunting Agent API is running", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here"),
    }


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a resume (PDF or DOCX), extract text, and analyze it with Groq AI.
    Returns structured resume data.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise HTTPException(
            status_code=400,
            detail="Groq API key not configured. Please add it to the .env file.",
        )

    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    }
    if file.content_type and file.content_type not in allowed_types:
        # Also allow by extension
        fname = file.filename or ""
        if not any(fname.lower().endswith(ext) for ext in [".pdf", ".docx", ".doc", ".txt"]):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a PDF, DOCX, or TXT file.",
            )

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    try:
        resume_text = parse_resume(file.filename or "resume.pdf", file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file.")

    try:
        resume_data = analyze_resume(resume_text)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True, "resume_data": resume_data}


@app.post("/api/search-jobs")
async def search_jobs(request: SearchRequest):
    """
    Search all job sources based on resume data and filters.
    Returns AI-ranked job listings.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise HTTPException(
            status_code=400,
            detail="Groq API key not configured. Please add it to the .env file.",
        )

    resume_data = request.resume_data
    if not resume_data:
        raise HTTPException(status_code=400, detail="Resume data is required.")

    # Generate search keywords from resume
    keywords = generate_search_keywords(resume_data)
    if request.custom_query and request.custom_query.strip():
        keywords.insert(0, request.custom_query.strip())

    # Search all sources in parallel
    try:
        jobs = await search_all_sources(
            keywords=keywords,
            location=request.location or "",
            work_mode_filter=request.work_mode or "Any",
            rapidapi_key=request.rapidapi_key or "",
            adzuna_app_id=request.adzuna_app_id or "",
            adzuna_app_key=request.adzuna_app_key or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search failed: {e}")

    if not jobs:
        return {
            "success": True,
            "jobs": [],
            "total": 0,
            "keywords_used": keywords,
            "message": "No jobs found for your search criteria. Try broadening the location or work mode.",
        }

    # AI ranking
    try:
        ranked_jobs = rank_jobs(resume_data, jobs)
    except Exception:
        ranked_jobs = jobs  # Fallback: return unranked

    return {
        "success": True,
        "jobs": ranked_jobs,
        "total": len(ranked_jobs),
        "keywords_used": keywords,
    }


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n*** AI Job Hunting Agent starting ***")
    print(">>> Open http://localhost:8000 in your browser\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
