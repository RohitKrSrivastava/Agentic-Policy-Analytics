from fastapi import APIRouter
from backend.app.api.endpoints import analysis, agents, datasets, llm_status, export

api_router = APIRouter()

api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis & Workflows"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent Logs & Execution"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Singapore Data Sources"])
api_router.include_router(llm_status.router, prefix="/llm", tags=["Multi-Cloud LLM Status"])
api_router.include_router(export.router, prefix="/export", tags=["Export & Artifacts"])
