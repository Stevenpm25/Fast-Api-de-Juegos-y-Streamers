from pydantic import BaseModel, Field
from typing import Optional

class Streamer(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    game: str = Field(..., min_length=2, max_length=50)
    follower_count: int = Field(..., ge=0)
    avg_viewers: int = Field(..., ge=0)

class StreamerWithID(Streamer):
    id: int

class UpdatedStreamer(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    game: Optional[str] = Field(None, min_length=2, max_length=50)
    follower_count: Optional[int] = Field(None, ge=0)
    avg_viewers: Optional[int] = Field(None, ge=0)