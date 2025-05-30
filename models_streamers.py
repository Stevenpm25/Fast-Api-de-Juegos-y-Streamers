from typing import Optional
from sqlmodel import SQLModel, Field


class StreamerBase(SQLModel):
    name: str = Field(..., min_length=2, max_length=100)
    game: str = Field(..., min_length=2, max_length=100)
    follower_count: int = Field(..., ge=0)
    avg_viewers: int = Field(..., ge=0)
# models_games.py

# models_streamers.py

class StreamerCreate(SQLModel):
    name: str = Field(..., min_length=2, max_length=100)
    game: str = Field(..., min_length=2, max_length=100)
    follower_count: int = Field(..., ge=0)
    avg_viewers: int = Field(..., ge=0)



class Streamer(StreamerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class StreamerWithID(SQLModel):
    id: int
    name: str
    game: str
    follower_count: int  # Nombre exacto como en la DB
    avg_viewers: int
    # Eliminar "followers", "total_streams", "peak_viewers" si no son necesarios
class UpdatedStreamer(SQLModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    game: Optional[str] = Field(default=None, min_length=2, max_length=100)
    follower_count: Optional[int] = Field(default=None, ge=0)
    avg_viewers: Optional[int] = Field(default=None, ge=0)

