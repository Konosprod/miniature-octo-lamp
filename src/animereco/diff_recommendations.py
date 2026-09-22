"""Compare our recommendation algorithm against AniList's own community-voted
`recommendations` for a given anime. Prints both lists side by side and their
difference -- this is a diff, not a quality score.

Usage: uv run python diff_recommendations.py <anime_id>
"""

import asyncio
import json
import sys

from api.crud import get_anime_recommendations
from db import Database
from models import Anime
from sqlalchemy import select

TOP_N = 10


def _title(titles: dict) -> str:
    return titles.get("romaji") or titles.get("english") or titles.get("native")


def _anilist_recommendations(doc: dict) -> dict[int, str]:
    recs = doc.get("recommendations") or "[]"
    if isinstance(recs, str):
        recs = json.loads(recs)

    ranked = sorted(recs, key=lambda rec: rec["node"].get("rating", 0), reverse=True)

    out = {}
    for rec in ranked:
        media = rec["node"].get("mediaRecommendation")
        if media is None:
            continue
        out[media["id"]] = _title(media["title"])
        if len(out) == TOP_N:
            break
    return out


def _print(label: str, items: dict[int, str]) -> None:
    print(f"{label} ({len(items)}):")
    for anime_id, title in items.items():
        print(f"  {anime_id}\t{title}")
    print()


async def main(anime_id: int) -> None:
    db = Database()

    async with db.get_session() as session:
        source = await session.scalar(select(Anime).where(Anime.anime_id == anime_id))
        if source is None:
            print(f"Anime {anime_id} not found in DB")
            return

        source_title = source.title_romaji or source.title_english or source.title_native
        print(f"Source: {source_title} (anime_id={anime_id})\n")

        ours = await get_anime_recommendations(session, anime_id)
        ours_by_id = {
            a.anime_id: (a.title_romaji or a.title_english or a.title_native) for a in ours
        }
        anilist_by_id = _anilist_recommendations(source.doc)

    await db.close()

    _print("Notre algo", ours_by_id)
    _print("AniList", anilist_by_id)

    common = ours_by_id.keys() & anilist_by_id.keys()
    only_ours = ours_by_id.keys() - anilist_by_id.keys()
    only_anilist = anilist_by_id.keys() - ours_by_id.keys()

    _print("Commun aux deux", {aid: ours_by_id[aid] for aid in common})
    _print("Seulement notre algo", {aid: ours_by_id[aid] for aid in only_ours})
    _print("Seulement AniList", {aid: anilist_by_id[aid] for aid in only_anilist})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python diff_recommendations.py <anime_id>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1])))
