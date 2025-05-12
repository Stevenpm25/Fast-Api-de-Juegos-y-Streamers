from pydantic import BaseModel, Field
from typing import Optional

class Game(BaseModel):
    date: str = Field(..., min_length=4, description="Fecha del registro en formato AAAA-MM")
    game: str = Field(..., min_length=1, max_length=100, description="Nombre del videojuego")
    hours_watched: int = Field(..., ge=0, description="Total de horas vistas")
    peak_viewers: int = Field(..., ge=0, description="Máximo de espectadores simultáneos")
    peak_channels: int = Field(..., ge=0, description="Máximo de canales transmitiendo el juego")

class GameWithID(Game):
    id: int

class UpdatedGame(BaseModel):
    date: Optional[str] = Field(None, min_length=4)
    game: Optional[str] = Field(None, min_length=1, max_length=100)
    hours_watched: Optional[int] = Field(None, ge=0)
    peak_viewers: Optional[int] = Field(None, ge=0)
    peak_channels: Optional[int] = Field(None, ge=0)
