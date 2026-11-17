from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables and trust defaults on startup
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization postponed (DB may still be starting): {e}")
    yield


app = FastAPI(
    title="Progressive Autonomy Agent Harness",
    description="Structural guardrail harness with calibrated trust and deterministic reversibility.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mock_llm_enabled": settings.MOCK_LLM_ENABLED,
        "trust_threshold": settings.TRUST_THRESHOLD
    }
