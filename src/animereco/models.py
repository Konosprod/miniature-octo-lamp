from calendar import c

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class Anime(Base):
    __tablename__ = "anime"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anime_id: Mapped[int] = mapped_column(Integer, nullable=True)
    doc: Mapped[str] = mapped_column(JSONB(none_as_null=True), nullable=True)
    vectors = mapped_column(Vector(3584), nullable=True)
    title_english = mapped_column(String, nullable=True)
    title_native = mapped_column(String, nullable=True)
    title_romaji = mapped_column(String, nullable=True)
    cover = mapped_column(String, nullable=True)


class AnimeMistral(Base):
    __tablename__ = "anime_mistral"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anime_id: Mapped[int] = mapped_column(Integer, nullable=True)
    doc: Mapped[str] = mapped_column(JSONB(none_as_null=True), nullable=True)
    vectors = mapped_column(Vector(1024), nullable=True)
    title_english = mapped_column(String, nullable=True)
    title_native = mapped_column(String, nullable=True)
    title_romaji = mapped_column(String, nullable=True)
    cover = mapped_column(String, nullable=True)
