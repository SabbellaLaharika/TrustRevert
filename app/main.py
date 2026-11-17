from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Progressive Autonomy Agent Harness",
    description="Structural guardrail harness with calibrated trust and deterministic reversibility.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mock_llm_enabled": settings.MOCK_LLM_ENABLED,
        "trust_threshold": settings.TRUST_THRESHOLD
    }
