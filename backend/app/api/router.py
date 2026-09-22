from fastapi import APIRouter

from app.api.claims import router as claims_router
from app.api.consensus import router as consensus_router
from app.api.claim_relations import router as claim_relations_router
from app.api.evidence import router as evidence_router
from app.api.entity_topic import router as entity_topic_router
from app.api.perspectives import router as perspectives_router
from app.api.search import router as search_router
from app.api.sources import router as sources_router
from app.api.stories import router as stories_router

api_router = APIRouter()

api_router.include_router(sources_router)
api_router.include_router(search_router)
api_router.include_router(entity_topic_router)
api_router.include_router(evidence_router)
api_router.include_router(stories_router)
api_router.include_router(claims_router)
api_router.include_router(claim_relations_router)
api_router.include_router(consensus_router)
api_router.include_router(perspectives_router)
