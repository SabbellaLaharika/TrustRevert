from fastapi import APIRouter
from app.api.agent import router as agent_router
from app.api.hitl import router as hitl_router
from app.api.system import router as system_router
from app.api.queue import router as queue_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(hitl_router)
api_router.include_router(system_router)
api_router.include_router(queue_router)

__all__ = ["api_router"]
