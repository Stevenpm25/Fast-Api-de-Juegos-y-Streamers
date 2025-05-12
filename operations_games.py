import csv
from typing import List, Optional
from models_games import Game, GameWithID, UpdatedGame

FILENAME_GAMES = "games.csv"
FIELDS_GAMES = ["id", "date", "game", "hours_watched", "peak_viewers", "peak_channels"]

# Leer todos los videojuegos
def read_all_games() -> List[GameWithID]:
    games = []
    try:
        with open(FILENAME_GAMES, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                row["id"] = int(row["id"])
                row["hours_watched"] = int(row["hours_watched"])
                row["peak_viewers"] = int(row["peak_viewers"])
                row["peak_channels"] = int(row["peak_channels"])
                games.append(GameWithID(**row))
    except FileNotFoundError:
        pass
    return games

# Leer un videojuego por ID
def read_one_game(game_id: int) -> Optional[GameWithID]:
    games = read_all_games()
    return next((g for g in games if g.id == game_id), None)

# Crear nuevo videojuego
def create_game(game: Game) -> GameWithID:
    games = read_all_games()
    new_id = max([g.id for g in games], default=0) + 1
    new_game = GameWithID(id=new_id, **game.model_dump())
    games.append(new_game)

    with open(FILENAME_GAMES, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS_GAMES)
        writer.writeheader()
        for g in games:
            writer.writerow(g.model_dump())
    return new_game

# Actualizar videojuego por ID
def update_game(game_id: int, update: UpdatedGame) -> Optional[GameWithID]:
    games = read_all_games()
    updated_game = None

    for i, g in enumerate(games):
        if g.id == game_id:
            data = g.model_dump()
            for key, value in update.model_dump(exclude_unset=True).items():
                data[key] = value
            updated_game = GameWithID(**data)
            games[i] = updated_game
            break

    if updated_game:
        with open(FILENAME_GAMES, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS_GAMES)
            writer.writeheader()
            for g in games:
                writer.writerow(g.model_dump())
    return updated_game

# Eliminar videojuego por ID
def delete_game(game_id: int) -> Optional[GameWithID]:
    games = read_all_games()
    remaining = []
    deleted = None
    for g in games:
        if g.id == game_id:
            deleted = g
        else:
            remaining.append(g)

    if deleted:
        with open(FILENAME_GAMES, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS_GAMES)
            writer.writeheader()
            for g in remaining:
                writer.writerow(g.model_dump())
    return deleted

# Buscar videojuegos por nombre parcial o año
def search_games(game_name: Optional[str] = None, year: Optional[str] = None) -> List[GameWithID]:
    games = read_all_games()

    if game_name:
        games = [g for g in games if game_name.lower() in g.game.lower()]

    if year:
        games = [g for g in games if g.date.startswith(year)]

    return games
