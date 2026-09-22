"""One-off backfill: merge AniList's `recommendations` field into `doc` for
anime rows that were loaded before this field was tracked. Reads the local
pickle only -- no Scaleway calls, no re-embedding.

Usage: uv run python backfill_recommendations.py
"""

import asyncio
import pickle
from pathlib import Path

from db import Database
from models import Anime
from sqlalchemy import select, update

BATCH_SIZE = 200


async def main() -> None:
    data = pickle.load(open(Path(__file__).parent / "data" / "anime.pkl", "rb"))
    recommendations_by_id = dict(zip(data["id"].astype(int), data["recommendations"]))

    db = Database()

    async with db.get_session() as session:
        rows = (await session.execute(select(Anime.anime_id, Anime.doc))).all()

    updated = 0
    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        async with db.get_session() as session:
            for anime_id, doc in batch:
                recs = recommendations_by_id.get(anime_id)
                if recs is None:
                    continue
                await session.execute(
                    update(Anime)
                    .where(Anime.anime_id == anime_id)
                    .values(doc={**doc, "recommendations": recs})
                )
                updated += 1

        print(f"  ... {min(batch_start + BATCH_SIZE, len(rows))}/{len(rows)}")

    print(f"Backfilled recommendations for {updated} anime")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
