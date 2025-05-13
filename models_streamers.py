from typing import Optional
from sqlmodel import SQLModel, Field


class StreamerBase(SQLModel):
    name: str = Field(..., min_length=2, max_length=50)
    game: str = Field(..., min_length=2, max_length=50)
    follower_count: int = Field(..., ge=0)
    avg_viewers: int = Field(..., ge=0)


class Streamer(StreamerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class StreamerWithID(StreamerBase):
    id: int


class UpdatedStreamer(SQLModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    game: Optional[str] = Field(default=None, min_length=2, max_length=50)
    follower_count: Optional[int] = Field(default=None, ge=0)
    avg_viewers: Optional[int] = Field(default=None, ge=0)
