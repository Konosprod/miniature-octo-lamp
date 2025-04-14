import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import animereco.api.crud as crud
from animereco.api.schemas import Anime, AnimeAutoComplete
from animereco.db import get_session

router = APIRouter(prefix="/anime", tags=["anime"])


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
    results = await crud.get_anime_by_anime_id(session, id)

    row_doc = results.doc

    row_doc["tags"] = json.loads(row_doc["tags"])
    row_doc["genres"] = json.loads(row_doc["genres"])

    return Anime(**results.doc)


@router.get("/{id}/recommendations", response_model=list[Anime])
async def get_top_10_ai_anime(
    id: int, session: Session = Depends(get_session)
) -> list[Anime]:
    """
    Get top 10 anime from the database.
    """
    results = await crud.get_top_10_ai_anime(session, id)

    ret = []

    for row in results:
        row.doc["tags"] = json.loads(row.doc["tags"])
        row.doc["genres"] = json.loads(row.doc["genres"])
        anime = Anime(**row.doc)
        anime.title_native = row.title_native
        anime.title_english = row.title_english
        anime.title_romaji = row.title_romaji
        anime.cover = row.cover

        ret.append(anime)

    return ret
