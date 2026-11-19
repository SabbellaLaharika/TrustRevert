from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables and default trust scores on startup (skip in test mode)
    if not settings.TESTING:
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


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mock_llm_enabled": settings.MOCK_LLM_ENABLED,
        "trust_threshold": settings.TRUST_THRESHOLD
    }
