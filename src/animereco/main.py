import asyncio
import math
import pickle
import time

import openai
from anyio import Path
from api.routes import router as api_router
from config import SCALEWAY_BASE_API, SCW_SECRET_KEY
from db import Database, db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from log import setup_logging
from models import Anime
from sqlalchemy import select
from utils import clean_html_string

logger = setup_logging(__name__)

EMBED_BATCH_SIZE = 32
EMBED_MAX_RETRIES = 5
EMBEDDING_DIMENSIONS = 4096


class ScalewayEmbedder:
    api_key: str
    model_name: str
    dimensions: int
    client: openai.OpenAI

    def __init__(self, model_name: str, api_key: str, base_url: str, dimensions: int):
        self.api_key = api_key
        self.model_name = model_name
        self.dimensions = dimensions
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def get_text_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        """Embed a batch of texts in a single API call, preserving input order."""
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model_name,
                    dimensions=self.dimensions,
                )
                ordered = sorted(response.data, key=lambda d: d.index)
                return [d.embedding for d in ordered]
            except openai.RateLimitError as e:
                delay = min(2**attempt, 30)
                logger.warning(
                    f"Rate limit exceeded (attempt {attempt + 1}/{EMBED_MAX_RETRIES}). "
                    f"Retrying in {delay}s: {e}"
                )
                time.sleep(delay)

        logger.error(
            f"Giving up on embedding batch of {len(texts)} texts "
            f"after {EMBED_MAX_RETRIES} attempts"
        )
        return [None] * len(texts)


def _json_safe_doc(doc: dict) -> dict:
    """Replace NaN/Inf floats (pandas' missing-value marker) with None.

    json.dumps() happily emits `NaN`, but that's not valid JSON and Postgres'
    jsonb parser rejects it outright.
    """
    return {
        key: (None if isinstance(value, float) and not math.isfinite(value) else value)
        for key, value in doc.items()
    }


def build_embedding_text(anime) -> str:
    """Free-text signal only: title + synopsis.

    Genres and tags are structured taxonomy data (AniList's fixed genre list
    and ranked tags), not free text — they're compared symbolically in
    crud.get_anime_recommendations (Jaccard / rank-weighted overlap) instead
    of being folded into the embedded text, where they'd just dilute the
    synopsis' semantic signal without adding anything an embedding model
    handles better than an exact/weighted set comparison.
    """
    concat_title = ""
    if anime["title_english"] is not None:
        concat_title = anime["title_english"] + " "
    if anime["title_native"] is not None:
        concat_title += anime["title_native"] + " "

    return concat_title + " " + clean_html_string(anime["description"])


async def load_anime(db: Database):
    logger.info("Starting to load anime data")
    data = pickle.load(open(Path(__file__).parent / "data" / "anime.pkl", "rb"))
    data = data.sort_values(by="id", ascending=True)
    data["id"] = data["id"].astype(int)

    data = data[
        [
            "id",
            "title_english",
            "title_native",
            "title_romaji",
            "description",
            "genres",
            "tags",
            "siteUrl",
            "coverImage_extraLarge",
            "relations",
            "averageScore",
            "meanScore",
            "popularity",
            "favourites",
            "recommendations",
        ]
    ]

    embedder = ScalewayEmbedder(
        model_name="qwen3-embedding-8b",
        api_key=SCW_SECRET_KEY,
        base_url=SCALEWAY_BASE_API,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    last_index = 0

    async with db.get_session() as session:
        last_entry = await session.scalar(
            select(Anime).order_by(Anime.anime_id.desc())
        )

        if last_entry is not None:
            last_index = last_entry.anime_id
            logger.debug(f"Last index: {last_index}")

    data = data[data["id"] > last_index]

    logger.info(f"Loading {len(data)} anime data")

    rows = list(data.iterrows())

    for batch_start in range(0, len(rows), EMBED_BATCH_SIZE):
        batch = rows[batch_start : batch_start + EMBED_BATCH_SIZE]
        texts = [build_embedding_text(anime) for _, anime in batch]
        embeddings = embedder.get_text_embeddings(texts)

        entities = []
        for (_, anime), embedding in zip(batch, embeddings):
            if embedding is None:
                logger.warning(f"Skipping anime {anime['id']}: embedding failed")
                continue

            entities.append(
                Anime(
                    anime_id=anime["id"],
                    doc=_json_safe_doc(anime.to_dict()),
                    vectors=embedding,
                    title_english=anime["title_english"],
                    title_native=anime["title_native"],
                    title_romaji=anime["title_romaji"],
                    cover=anime["coverImage_extraLarge"],
                )
            )

        try:
            async with db.get_session() as session:
                session.add_all(entities)
        except Exception:
            ids = [anime["id"] for _, anime in batch]
            logger.exception(
                f"Failed to insert batch {batch_start // EMBED_BATCH_SIZE + 1} "
                f"(anime ids {ids}); skipping batch and continuing"
            )
            continue

        logger.info(
            f"Loaded batch {batch_start // EMBED_BATCH_SIZE + 1} "
            f"({min(batch_start + EMBED_BATCH_SIZE, len(rows))}/{len(rows)} anime)"
        )


async def lifespan(app: FastAPI):
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Anime Recommender API", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="front/static"), name="static")
templates = Jinja2Templates(directory="front/templates")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html")


async def main():
    db = Database()
    await db.init_db()

    await load_anime(db)


if __name__ == "__main__":
    asyncio.run(main())
