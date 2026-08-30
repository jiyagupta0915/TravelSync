from fastapi import APIRouter

from app.database import database_status
from app.services.recommendation_engine import DF, TRAVELLER_TYPES, INTEREST_FEATURES, FEATURES

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
async def health():
    db_ok, db_name = await database_status()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "TravelSync API",
        "destinations": int(len(DF)),
        "model": "Weighted KNN content similarity + constraint ranking",
        "database": {"connected": db_ok, "name": db_name},
    }


@router.get("/features")
async def features():
    return {
        "features": FEATURES,
        "interest_features": INTEREST_FEATURES,
        "traveller_types": TRAVELLER_TYPES,
        "importance_levels": {"Must have": 3, "Nice to have": 2, "Optional": 1},
    }
