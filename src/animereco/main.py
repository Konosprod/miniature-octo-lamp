from llama_index.embeddings.mistralai import MistralAIEmbedding
from sqlalchemy import select

from animereco.anilist import Anilist
from animereco.config import MISTRAL_API_KEY
from animereco.db import Database
from animereco.models import AnimeMistral
from animereco.utils import clean_html_string


def main():
    db = Database()
    db.init_db()

    anilist = Anilist()

    anime = anilist.get_random_anime()
    anime["description"] = clean_html_string(anime["description"])

    concat_genre = " ".join(anime["genres"])

    concat_tags = ""

    for tag in anime["tags"]:
        concat_tags += tag["name"] + " "
    concat_tags = concat_tags[:-1]

    concat_title = ""

    if anime["title"]["english"] is not None:
        concat_title = anime["title"]["english"] + " "
    if anime["title"]["native"] is not None:
        concat_title += anime["title"]["native"] + " "

    to_embed = (
        concat_title
        + " "
        + anime["description"]
        + " "
        + concat_genre
        + " "
        + concat_tags
    )

    api_key = MISTRAL_API_KEY
    model_name = "mistral-embed"
    embed_model = MistralAIEmbedding(model_name=model_name, api_key=api_key)
    embeddings = embed_model.get_text_embedding(to_embed)

    anime_entity = AnimeMistral(
        title=anime["title"]["english"],
        doc=anime,
        vectors=embeddings,
    )

    with db.get_session() as session:
        session.add(anime_entity)
        session.commit()

        to_compare = session.query(AnimeMistral).first()

        res = session.scalars(
            select(AnimeMistral)
            .order_by(AnimeMistral.vectors.l2_distance(to_compare.vectors))
            .limit(2)
        ).fetchmany()

        print(to_compare.title)
        print(res[1].title)

    # client = OpenAI(api_key=SCALEWAY_API_KEY, base_url=SCALEWAY_BASE_API)

    # embedding_response = client.embeddings.create(
    #     input="Hello world",
    #     model="bge-multilingual-gemma2",
    # )

    # print(embedding_response.data[0].embedding)
