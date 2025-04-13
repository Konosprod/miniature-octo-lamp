from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class Anime(Base):
    __tablename__ = "anime"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anime_id: Mapped[int] = mapped_column(Integer, nullable=True)
    doc: Mapped[str] = mapped_column(JSON(), nullable=True)
    vectors = mapped_column(Vector(3584), nullable=True)


class AnimeMistral(Base):
    __tablename__ = "anime_mistral"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anime_id: Mapped[int] = mapped_column(Integer, nullable=True)
    doc: Mapped[str] = mapped_column(JSON(), nullable=True)
    vectors = mapped_column(Vector(1024), nullable=True)
