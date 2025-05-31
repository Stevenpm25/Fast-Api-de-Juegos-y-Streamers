from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class GameBase(SQLModel):
    date: str = Field(..., min_length=4, description="Fecha del registro en formato AAAA-MM")
    game: str = Field(..., min_length=1, max_length=1000, description="Nombre del videojuego")
    hours_watched: int = Field(..., ge=0, description="Total de horas vistas")
    peak_viewers: int = Field(..., ge=0, description="Máximo de espectadores simultáneos")
    peak_channels: int = Field(..., ge=0, description="Máximo de canales transmitiendo el juego")
    image_url: Optional[str] = Field(default=None, description="URL de la imagen del juego en Supabase")

class Game(GameBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class GameWithID(GameBase):
    id: int

class GameCreate(GameBase):
    pass

class UpdatedGame(SQLModel):
    date: Optional[str] = Field(default=None, min_length=4)
    game: Optional[str] = Field(default=None, min_length=1, max_length=100)
    hours_watched: Optional[int] = Field(default=None, ge=0)
    peak_viewers: Optional[int] = Field(default=None, ge=0)
    peak_channels: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = Field(default=None)