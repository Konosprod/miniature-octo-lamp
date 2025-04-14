from pydantic import BaseModel


class AnimeAutoComplete(BaseModel):
    anime_id: int
    title_english: str | None = None
    title_native: str | None = None
    title_romaji: str | None = None


class Tag(BaseModel):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    rank: int | None = None
    isGeneralSpoiler: bool | None = None
    isMediaSpoiler: bool | None = None
    isAdult: bool | None = None


class Anime(BaseModel):
    id: int
    title_english: str | None = None
    title_native: str | None = None
    title_romaji: str | None = None
    description: str | None = None
    genres: list[str] | None = None
    tags: list[Tag] | None = None
    siteUrl: str | None = None

    class Config:
        from_attributes = True
