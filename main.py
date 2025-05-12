from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from models_streamers import *
from operations_streamers import *
from operations_games import *
from models_games import Game, GameWithID, UpdatedGame


app = FastAPI()

@app.get("/")
def root():
    return {"message": "API para analizar streamers y videojuegos"}

# ------------------- STREAMERS -------------------

@app.get("/streamers/search", response_model=List[StreamerWithID])
def search_streamers_endpoint(
    name: Optional[str] = Query(None, description="Nombre parcial o completo del streamer"),
    game: Optional[str] = Query(None, description="Filtrar por el nombre del videojuego que transmite")
):
    results = search_streamers(name=name, game=game)  # <--- Cambiado game_title a game
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron streamers que coincidan")
    return results

@app.get("/streamers", response_model=List[StreamerWithID])
def get_all_streamers():
    return read_all_streamers()

@app.get("/streamers/{streamer_id}", response_model=StreamerWithID)
def get_streamer(streamer_id: int):
    streamer = read_one_streamer(streamer_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer no encontrado")
    return streamer

@app.post("/streamers", response_model=StreamerWithID)
def post_streamer(streamer: Streamer):
    return create_streamer(streamer)

@app.put("/streamers/{streamer_id}", response_model=StreamerWithID)
def put_streamer(streamer_id: int, streamer_update: UpdatedStreamer):
    updated = update_streamer(streamer_id, streamer_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Streamer no encontrado para actualizar")
    return updated

@app.delete("/streamers/{streamer_id}", response_model=StreamerWithID)
def delete_streamer_by_id(streamer_id: int):
    deleted = delete_streamer(streamer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Streamer no encontrado para eliminar")
    return deleted

# ------------------- VIDEOJUEGOS -------------------

@app.get("/games/search", response_model=List[GameWithID])
def search_games_endpoint(
    game_name: Optional[str] = Query(None, description="Nombre parcial del videojuego"),
    year: Optional[str] = Query(None, description="Filtrar por año (ej: 2022)")
):
    results = search_games(game_name=game_name, year=year)
    if not results:
        raise HTTPException(status_code=404, detail="No se encontraron videojuegos que coincidan")
    return results
@app.get("/games", response_model=List[GameWithID])
def get_all_games():
    return read_all_games()

@app.get("/games/{game_id}", response_model=GameWithID)
def get_game(game_id: int):
    game = read_one_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Videojuego no encontrado")
    return game

@app.post("/games", response_model=GameWithID)
def post_game(game: Game):
    return create_game(game)

@app.put("/games/{game_id}", response_model=GameWithID)
def put_game(game_id: int, game_update: UpdatedGame):
    updated = update_game(game_id, game_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Videojuego no encontrado para actualizar")
    return updated

@app.delete("/games/{game_id}", response_model=GameWithID)
def delete_game_by_id(game_id: int):
    deleted = delete_game(game_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Videojuego no encontrado para eliminar")
    return deleted




