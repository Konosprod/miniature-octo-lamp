import asyncio
import json
import pickle
import time

import mistralai
from anyio import Path
from api.routes import router as api_router
from config import MISTRAL_API_KEY
from db import Database, db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from llama_index.embeddings.mistralai import MistralAIEmbedding
from log import setup_logging
from models import AnimeMistral
from sqlalchemy import select
from utils import clean_html_string

logger = setup_logging(__name__)


class MistralEmbedder:
    api_key: str
    model_name: str
    model: MistralAIEmbedding

    def __init__(self, model_name: str, api_key: str):
        self.api_key = api_key
        self.model_name = model_name
        self.model = MistralAIEmbedding(model_name=model_name, api_key=api_key)

    def get_text_embedding(self, text: str):
        try:
            embedding = self.model.get_text_embedding(text)
            return embedding
        except mistralai.models.sdkerror.SDKError as e:
            if e.status_code == 429:
                logger.debug(f"Rate limit exceeded. Retrying in 1 second: {e.message}")
                time.sleep(1)
                return self.get_text_embedding(text)
            return None


def load_anime(db: Database):
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
        ]
    ]

    embedder = MistralEmbedder(
        model_name="mistral-embed",
        api_key=MISTRAL_API_KEY,
    )

    last_index = 0

    with db.get_session() as session:
        last_entry = (
            session.query(AnimeMistral).order_by(AnimeMistral.anime_id.desc()).first()
        )

        if last_entry is not None:
            last_index = last_entry.anime_id
            logger.debug(f"Last index: {last_index}")

    data = data[data["id"] > last_index]

    logger.info(f"Loading {len(data)} anime data")

    for _, anime in data.iterrows():
        genres = json.loads(anime["genres"])

        for genre in genres:
            concat_genre = genre + " "
        concat_genre = concat_genre[:-1]

        concat_tags = ""

        tags = json.loads(anime["tags"])

        for tag in tags:
            concat_tags += tag["name"] + " " + tag["description"] + " "
        concat_tags = concat_tags[:-1]

        concat_title = ""

        if anime["title_english"] is not None:
            concat_title = anime["title_english"] + " "
        if anime["title_native"] is not None:
            concat_title += anime["title_native"] + " "

        logger.debug(f"SiteURL: {anime['siteUrl']}")

        to_embed = (
            concat_title
            + " "
            + clean_html_string(anime["description"])
            + " "
            + concat_genre
            + " "
            + concat_tags
        )

        embedding = embedder.get_text_embedding(to_embed)

        anime_entity = AnimeMistral(
            anime_id=anime["id"],
            doc=anime.to_dict(),
            vectors=embedding,
            title_english=anime["title_english"],
            title_native=anime["title_native"],
            title_romaji=anime["title_romaji"],
        )

        with db.get_session() as session:
            session.add(anime_entity)
            session.commit()
            logger.debug(f"Added anime {anime['id']} to database")


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
    return templates.TemplateResponse("index.html", {"request": request})


async def main():
    db = Database()
    await db.init_db()

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
        ]
    ]

    async with db.get_session() as session:
        async with session.begin():
            for _, anime in data.iterrows():
                res = await session.scalar(
                    select(AnimeMistral).where(AnimeMistral.anime_id == anime["id"])
                )

                if res is None:
                    logger.debug(f"Anime {anime['id']} not found in database")
                    continue
                else:
                    res.cover = anime["coverImage_extraLarge"]
                    session.add(res)

    # with db.get_session() as session:
    #     to_compare = session.scalar(
    #         select(AnimeMistral).where(AnimeMistral.anime_id == 127690)
    #     )

    #     if to_compare is None:
    #         logger.error("Anime not found in database")
    #         return
    #     res = session.scalars(
    #         select(AnimeMistral)
    #         .order_by(AnimeMistral.vectors.l2_distance(to_compare.vectors))
    #         .limit(10)
    #     ).fetchmany()

    #     for anime in res[1:]:
    #         logger.debug(f"Anime ID: {anime.anime_id}")
    #         logger.debug(
    #             f"Title: {anime.doc['title_english']} | {anime.doc['title_native']}"
    #        )

    # load_anime(db)

    #     to_compare = session.query(AnimeMistral).first()

    #     res = session.scalars(
    #         select(AnimeMistral)
    #         .order_by(AnimeMistral.vectors.l2_distance(to_compare.vectors))
    #         .limit(2)
    #     ).fetchmany()

    #     print(to_compare.title)
    #     print(res[1].title)

    # client = OpenAI(api_key=SCALEWAY_API_KEY, base_url=SCALEWAY_BASE_API)

    # embedding_response = client.embeddings.create(
    #     input="Hello world",
    #     model="bge-multilingual-gemma2",
    # )

    # print(embedding_response.data[0].embedding)


if __name__ == "__main__":
    asyncio.run(main())
