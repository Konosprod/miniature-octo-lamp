import json
import pickle
import time

import mistralai
from anyio import Path
from llama_index.embeddings.mistralai import MistralAIEmbedding
from numpy import concat
from openai import api_key
from sqlalchemy import select

from animereco.anilist import Anilist
from animereco.config import MISTRAL_API_KEY
from animereco.db import Database
from animereco.log import setup_logging
from animereco.models import AnimeMistral
from animereco.utils import clean_html_string

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


def main():
    db = Database()
    db.init_db()

    data = pickle.load(open(Path(__file__).parent / "data" / "anime.pkl", "rb"))
    data = data.sort_values(by="id", ascending=True)

    embedder = MistralEmbedder(
        model_name="mistral-embed",
        api_key=MISTRAL_API_KEY,
    )

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
            doc=anime.to_json(),
            vectors=embedding,
        )

        with db.get_session() as session:
            session.add(anime_entity)
            session.commit()
            logger.debug(f"Added anime {anime['id']} to database")

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
    main()
