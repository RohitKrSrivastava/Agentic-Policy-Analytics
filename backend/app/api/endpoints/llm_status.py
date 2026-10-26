from datetime import datetime

from fastapi import APIRouter

from backend.app.config import settings
from backend.app.llm.router import llm_router
from backend.app.models.schemas import SystemHealthResponse

router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def get_multi_cloud_health():
    """
    Returns real-time status, latency, and model info for all integrated LLM providers
    (OpenAI, Google Cloud Gemini, AWS Bedrock, Local Deterministic Fallback).
    """
    providers_health = await llm_router.get_providers_health()
    return SystemHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        active_providers=providers_health,
        default_strategy=settings.LLM_PROVIDER_PRIORITY,
        total_analyses_run=14 # illustrative baseline counter
    )
