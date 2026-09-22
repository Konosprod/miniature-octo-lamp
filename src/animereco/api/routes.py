import json

import api.crud as crud
import models
from api.schemas import Anime, AnimeAutoComplete, RecommendationComparison
from db import get_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/anime", tags=["anime"])


def _to_schema(row: models.Anime) -> Anime:
    """Convert a DB row (doc JSONB + a few dedicated columns) to the API schema."""
    doc = dict(row.doc)
    doc["tags"] = json.loads(doc["tags"]) if isinstance(doc.get("tags"), str) else doc.get("tags")
    doc["genres"] = (
        json.loads(doc["genres"]) if isinstance(doc.get("genres"), str) else doc.get("genres")
    )

    anime = Anime(**doc)
    anime.title_english = row.title_english
    anime.title_native = row.title_native
    anime.title_romaji = row.title_romaji
    anime.cover = row.cover
    return anime


@router.get("/autocomplete", response_model=list[AnimeAutoComplete])
async def get_anime(search: str, session: Session = Depends(get_session)):
    """
    Get anime data from the database.
    """
    results = await crud.get_anime_autocomplete(session, search)
    return results


@router.get("/{id}", response_model=Anime)
async def get_anime_by_id(id: int, session: Session = Depends(get_session)) -> Anime:
    """
    Get anime data from the database.
    """
    row = await crud.get_anime_by_anime_id(session, id)
    if row is None:
        raise HTTPException(status_code=404, detail="Anime not found")
    return _to_schema(row)


@router.get("/{id}/recommendations", response_model=RecommendationComparison)
async def get_anime_recommendations(
    id: int, session: Session = Depends(get_session)
) -> RecommendationComparison:
    """
    Get anime recommendations for a given anime: both our own algorithm's
    picks and AniList's own community-voted recommendations, so they can be
    compared side by side.
    """
    source = await crud.get_anime_by_anime_id(session, id)
    if source is None:
        raise HTTPException(status_code=404, detail="Anime not found")

    ours = await crud.get_anime_recommendations(session, id)
    anilist = await crud.get_anilist_recommendations(session, id)

    return RecommendationComparison(
        source=_to_schema(source),
        ours=[_to_schema(row) for row in ours],
        anilist=[_to_schema(row) for row in anilist],
    )
