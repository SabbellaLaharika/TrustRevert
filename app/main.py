import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.core.config import settings
from app.core.database import init_db
from app.api import api_router

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables and default trust scores on startup (skip in test mode)
    is_testing = settings.TESTING or "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
    if not is_testing:
        try:
            init_db()
        except Exception as e:
            print(f"Warning: Database initialization postponed: {e}")
    yield


app = FastAPI(
    title="Progressive Autonomy Agent Harness",
    description="Structural guardrail harness with calibrated trust and deterministic reversibility.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount all API routes
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard():
    """Serves the interactive Agent Operations & Structural Guardrail Console."""
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>TrustRevert API is Running.</h1>"


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mock_llm_enabled": settings.MOCK_LLM_ENABLED,
        "trust_threshold": settings.TRUST_THRESHOLD
    }
