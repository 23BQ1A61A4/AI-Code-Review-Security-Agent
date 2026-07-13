"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Module 1 wired up the Code Submission Module. Module 2 added the Code
Analysis Agent's endpoints. Module 3 adds the Security Vulnerability
Agent's endpoints. Later modules will include additional routers here
(remediation, PR summary, chat, reports) the same way — just another
`app.include_router(...)` line, nothing else changes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis_routes import router as analysis_router
from app.api.security_routes import router as security_router
from app.api.submission_routes import router as submission_router
from app.config import CORS_ALLOW_ORIGINS

app = FastAPI(
    title="AI Code Review & Security Analysis Agent — Backend",
    description="Backend API for the multi-agent code review platform (Infosys spec).",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submission_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(security_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-code-review-backend", "module": "3 - security vulnerability agent"}


