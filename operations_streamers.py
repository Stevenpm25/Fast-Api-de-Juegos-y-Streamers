import csv
from typing import Optional, List
from models import Streamer, StreamerWithID, UpdatedStreamer

FILENAME = "streamers.csv"
FIELDS = ["id", "name", "game", "follower_count", "avg_viewers"]  # Eliminado uses_makeup




def read_all_streamers() -> List[StreamerWithID]:
    streamers = []
    with open(FILENAME, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            streamers.append(StreamerWithID(
                id=int(row["id"]),
                name=row["name"],
                game=row["game"],
                follower_count=int(row["follower_count"]),
                avg_viewers=int(row["avg_viewers"]),
            ))
    return streamers



# Leer un streamer por ID
def read_one_streamer(streamer_id: int) -> Optional[StreamerWithID]:
    streamers = read_all_streamers()
    for s in streamers:
        if s.id == streamer_id:
            return s
    return None


# Obtener el siguiente ID
def get_next_id() -> int:
    try:
        streamers = read_all_streamers()
        return max(s.id for s in streamers) + 1 if streamers else 1
    except FileNotFoundError:
        return 1


# Crear un nuevo streamer
def create_streamer(streamer: Streamer) -> StreamerWithID:
    new_id = get_next_id()
    new_streamer = StreamerWithID(id=new_id, **streamer.model_dump())
    with open(FILENAME, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writerow(new_streamer.model_dump())
    return new_streamer


# Actualizar un streamer
def update_streamer(streamer_id: int, update: UpdatedStreamer) -> Optional[StreamerWithID]:
    streamers = read_all_streamers()
    updated_streamer = None
    for i, s in enumerate(streamers):
        if s.id == streamer_id:
            data = s.model_dump()
            for key, value in update.model_dump(exclude_unset=True).items():
                data[key] = value
            updated_streamer = StreamerWithID(**data)
            streamers[i] = updated_streamer
            break

    if updated_streamer:
        with open(FILENAME, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            for s in streamers:
                writer.writerow(s.model_dump())
        return updated_streamer
    return None


# Eliminar un streamer
def delete_streamer(streamer_id: int) -> Optional[StreamerWithID]:
    streamers = read_all_streamers()
    remaining = []
    deleted = None
    for s in streamers:
        if s.id == streamer_id:
            deleted = s
        else:
            remaining.append(s)

    if deleted:
        with open(FILENAME, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            for s in remaining:
                writer.writerow(s.model_dump())
    return deleted


# Buscar streamers por nombre o videojuego
def search_streamers(name: str = None, game: str = None) -> List[StreamerWithID]:
    streamers = read_all_streamers()

    if name:
        streamers = [s for s in streamers if name.lower() in s.name.lower()]

    if game:
        streamers = [s for s in streamers if game.lower() in s.game.lower()]

    return streamers
