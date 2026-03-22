from fastapi import APIRouter

from app.api.v1.leagues import router as leagues_router
from app.api.v1.matches import router as matches_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.standings import router as standings_router
from app.api.v1.teams import router as teams_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(leagues_router)
api_router.include_router(matches_router)
api_router.include_router(predictions_router)
api_router.include_router(standings_router)
api_router.include_router(teams_router)
