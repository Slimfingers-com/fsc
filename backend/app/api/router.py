from fastapi import APIRouter

from app.api.sources import router as sources_router
from app.api.search import router as search_router

api_router = APIRouter()

api_router.include_router(sources_router)
api_router.include_router(search_router)
