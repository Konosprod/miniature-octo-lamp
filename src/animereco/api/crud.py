import json

from models import Anime
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

FRANCHISE_RELATION_TYPES = {
    "SEQUEL",
    "PREQUEL",
    "SIDE_STORY",
    "SPIN_OFF",
    "ALTERNATIVE",
    "SUMMARY",
}

CANDIDATE_POOL_SIZE = 40
RESULT_LIMIT = 10
ANILIST_RESULT_LIMIT = 10
SIMILARITY_WEIGHT = 0.55
GENRE_WEIGHT = 0.15
TAG_WEIGHT = 0.2
POPULARITY_WEIGHT = 0.1
POPULARITY_REF = 5000


def _franchise_neighbors(doc: dict) -> set[int]:
    """AniList ids directly linked to `doc` as same-franchise media."""
    relations = doc.get("relations") or "[]"
    if isinstance(relations, str):
        relations = json.loads(relations)

    return {
        rel["node"]["id"]
        for rel in relations
        if rel.get("relationType") in FRANCHISE_RELATION_TYPES
        and rel.get("node", {}).get("type") == "ANIME"
    }


async def _franchise_closure(session: Session, doc: dict, source_anime_id: int) -> set[int]:
    """Transitive closure of same-franchise media (sequels, spin-offs, ...) to exclude.

    AniList's `relations` are direct edges only (S1->S2, S2->S3, ...), not a
    fully-connected franchise graph, so a season 1 entry won't directly list
    season 3+ as related. We BFS through the relation graph instead, fetching
    each newly-discovered anime's own relations from the DB as we go.
    """
    visited = {source_anime_id}
    frontier = _franchise_neighbors(doc)

    while frontier - visited:
        new_ids = frontier - visited
        visited |= new_ids

        stmt = select(Anime.doc).where(Anime.anime_id.in_(list(new_ids)))
        results = await session.execute(stmt)
        frontier = set()
        for (neighbor_doc,) in results:
            frontier |= _franchise_neighbors(neighbor_doc)

    visited.discard(source_anime_id)
    return visited


def _genres(doc: dict) -> set[str]:
    genres = doc.get("genres") or "[]"
    if isinstance(genres, str):
        genres = json.loads(genres)
    return set(genres)


def _genre_jaccard(source_genres: set[str], candidate_genres: set[str]) -> float:
    if not source_genres or not candidate_genres:
        return 0.0
    return len(source_genres & candidate_genres) / len(source_genres | candidate_genres)


def _tag_weights(doc: dict) -> dict[str, float]:
    """Tag name -> relevance (AniList's `rank`, 0-100, normalized to 0-1)."""
    tags = doc.get("tags") or "[]"
    if isinstance(tags, str):
        tags = json.loads(tags)
    return {tag["name"]: (tag.get("rank") or 0) / 100 for tag in tags}


def _weighted_tag_overlap(source_tags: dict[str, float], candidate_tags: dict[str, float]) -> float:
    """Ruzicka similarity (weighted Jaccard): sum(min) / sum(max) over the union of tags."""
    keys = source_tags.keys() | candidate_tags.keys()
    if not keys:
        return 0.0
    numerator = sum(min(source_tags.get(k, 0), candidate_tags.get(k, 0)) for k in keys)
    denominator = sum(max(source_tags.get(k, 0), candidate_tags.get(k, 0)) for k in keys)
    return numerator / denominator if denominator else 0.0


async def get_anime_autocomplete(session: Session, search: str) -> list[Anime]:
    """
    Get anime data from the database.
    """
    stmt = select(Anime).where(
        or_(
            Anime.title_english.ilike(f"{search}%"),
            Anime.title_native.ilike(f"{search}%"),
            Anime.title_romaji.ilike(f"{search}%"),
        )
    )

    results = await session.execute(stmt)
    animes = results.scalars().all()
    return animes


async def get_anime_by_anime_id(session: Session, id: int) -> Anime:
    """
    Get anime data from the database.
    """
    stmt = select(Anime).where(Anime.anime_id == id)
    results = await session.execute(stmt)
    anime = results.scalars().first()
    return anime


async def get_anime_recommendations(session: Session, id: int) -> list[Anime]:
    """
    Get anime recommendations for a given anime.

    Retrieves a candidate pool by cosine similarity (pgvector), excludes
    same-franchise media (sequels, spin-offs, ...), then re-ranks the pool
    with a composite score blending embedding similarity (title + synopsis),
    genre overlap, rank-weighted tag overlap, and popularity.
    """
    stmt = select(Anime).where(Anime.anime_id == id)
    res = await session.execute(stmt)
    anime = res.scalars().first()

    if anime is None:
        return []

    excluded_ids = await _franchise_closure(session, anime.doc, id) | {id}
    source_genres = _genres(anime.doc)
    source_tags = _tag_weights(anime.doc)

    distance = Anime.vectors.cosine_distance(anime.vectors).label("distance")
    stmt = (
        select(Anime, distance)
        .where(Anime.anime_id.notin_(list(excluded_ids)))
        .order_by(distance)
        .limit(CANDIDATE_POOL_SIZE)
    )

    results = await session.execute(stmt)
    candidates = results.all()

    scored = []
    for candidate, dist in candidates:
        similarity = 1 - dist
        genre_score = _genre_jaccard(source_genres, _genres(candidate.doc))
        tag_score = _weighted_tag_overlap(source_tags, _tag_weights(candidate.doc))
        popularity_score = min((candidate.doc.get("popularity") or 0) / POPULARITY_REF, 1.0)

        score = (
            SIMILARITY_WEIGHT * similarity
            + GENRE_WEIGHT * genre_score
            + TAG_WEIGHT * tag_score
            + POPULARITY_WEIGHT * popularity_score
        )
        scored.append((score, candidate))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _, candidate in scored[:RESULT_LIMIT]]


async def get_anilist_recommendations(session: Session, id: int) -> list[Anime]:
    """
    AniList's own community-voted recommendations for a given anime,
    resolved against our own anime table (so we get cover/synopsis/etc.),
    ranked by AniList's vote `rating`. Entries AniList recommends that we
    haven't loaded ourselves are silently skipped.
    """
    stmt = select(Anime).where(Anime.anime_id == id)
    res = await session.execute(stmt)
    anime = res.scalars().first()

    if anime is None:
        return []

    recs = anime.doc.get("recommendations") or "[]"
    if isinstance(recs, str):
        recs = json.loads(recs)

    ranked = sorted(recs, key=lambda rec: rec["node"].get("rating", 0), reverse=True)

    ordered_ids = []
    for rec in ranked:
        media = rec["node"].get("mediaRecommendation")
        if media is not None:
            ordered_ids.append(media["id"])
        if len(ordered_ids) == ANILIST_RESULT_LIMIT:
            break

    if not ordered_ids:
        return []

    stmt = select(Anime).where(Anime.anime_id.in_(ordered_ids))
    results = await session.execute(stmt)
    by_id = {a.anime_id: a for a in results.scalars().all()}

    return [by_id[i] for i in ordered_ids if i in by_id]
