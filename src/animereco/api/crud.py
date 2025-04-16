from models import AnimeMistral
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


async def get_anime_autocomplete(session: Session, search: str) -> list[AnimeMistral]:
    """
    Get anime data from the database.
    """
    stmt = select(AnimeMistral).where(
        or_(
            AnimeMistral.title_english.ilike(f"{search}%"),
            AnimeMistral.title_native.ilike(f"{search}%"),
            AnimeMistral.title_romaji.ilike(f"{search}%"),
        )
    )

    results = await session.execute(stmt)
    animes = results.scalars().all()
    return animes


async def get_anime_by_anime_id(session: Session, id: int) -> AnimeMistral:
    """
    Get anime data from the database.
    """
    stmt = select(AnimeMistral).where(AnimeMistral.anime_id == id)
    results = await session.execute(stmt)
    anime = results.scalars().first()
    return anime


async def get_top_10_ai_anime(session: Session, id: int) -> list[AnimeMistral]:
    """
    Get top 10 anime from the database.
    """
    stmt = (
        select(AnimeMistral)
        .where(AnimeMistral.anime_id == id)
        .order_by(AnimeMistral.vectors.l2_distance(id))
        .limit(10)
    )

    stmt = select(AnimeMistral).where(AnimeMistral.anime_id == id)

    res = await session.execute(stmt)
    anime = res.scalars().first()

    stmt = (
        select(AnimeMistral)
        .order_by(AnimeMistral.vectors.l2_distance(anime.vectors))
        .limit(10)
    )

    results = await session.execute(stmt)
    animes = results.scalars().all()
    animes = [anime for anime in animes if anime.anime_id != id]
    return animes
