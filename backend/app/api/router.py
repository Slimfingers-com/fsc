from fastapi import APIRouter

from app.api.sources import router as sources_router
from app.api.search import router as search_router
from app.api.entity_topic import router as entity_topic_router

api_router = APIRouter()

api_router.include_router(sources_router)
api_router.include_router(search_router)
api_router.include_router(entity_topic_router)
