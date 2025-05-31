from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models_games import Game, GameWithID, UpdatedGame,GameCreate, Game
from fastapi import UploadFile
import os
import csv
from image_operations import upload_game_image  # Importar aquí para evitar dependencia circular


async def read_all_games(session: AsyncSession) -> List[GameWithID]:
    result = await session.execute(select(Game))
    return result.scalars().all()



async def read_one_game(session: AsyncSession, game_id: int) -> Optional[GameWithID]:
    return await session.get(Game, game_id)


async def create_game(session: AsyncSession, game: GameCreate) -> Game:
    new_game = Game(**game.dict())
    session.add(new_game)
    await session.commit()
    await session.refresh(new_game)
    return new_game



async def update_game(session: AsyncSession, game_id: int, update: UpdatedGame) -> Optional[GameWithID]:
    existing = await session.get(Game, game_id)
    if not existing:
        return None

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def delete_game(session: AsyncSession, game_id: int) -> Optional[GameWithID]:
    existing = await session.get(Game, game_id)
    if not existing:
        return None

    # Convertimos a objeto plano
    plain_game = GameWithID.model_validate(existing)

    # Guardamos en CSV SIN await
    store_deleted_game(plain_game)

    # Eliminamos de la base
    await session.delete(existing)
    await session.commit()
    return plain_game

async def search_games(session: AsyncSession, game_name: str = None) -> List[GameWithID]:
    try:
        query = select(Game)

        if game_name:
            # Convertir a minúsculas para búsqueda sin distinción entre mayúsculas y minúsculas
            # y eliminar espacios al inicio y final
            search_name = game_name.lower().strip()

            # Buscar coincidencias parciales en cualquier parte del nombre
            query = query.where(Game.game.ilike(f"%{search_name}%"))

        result = await session.execute(query)
        games = result.scalars().all()
        return list(games)

    except Exception as e:
        print(f"Error en la búsqueda de juegos: {str(e)}")
        return []
# ✅ Operación para importar todos los videojuegos desde CSV a la base de datos
async def import_games_from_csv(session: AsyncSession, csv_path: str = "games.csv") -> int:
    inserted = 0
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            game = Game(
                date=row["date"],
                game=row["game"],
                hours_watched=int(row["hours_watched"]),
                peak_viewers=int(row["peak_viewers"]),
                peak_channels=int(row["peak_channels"]),
            )
            session.add(game)
            inserted += 1
    await session.commit()
    return inserted
def store_deleted_game(deleted_game: GameWithID):
    eliminados_path = "eliminados.csv"

    # Leer datos existentes para evitar duplicados
    existing_ids = set()
    existing_rows = []
    fieldnames = ["id", "date", "game", "hours_watched", "peak_viewers", "peak_channels", "image_url"]

    if os.path.exists(eliminados_path):
        with open(eliminados_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("id") and int(row["id"]) != deleted_game.id:
                    existing_rows.append(row)
                    existing_ids.add(int(row["id"]))

    # Preparar los datos del juego eliminado
    game_data = {
        "id": deleted_game.id,
        "date": deleted_game.date,
        "game": deleted_game.game,
        "hours_watched": deleted_game.hours_watched,
        "peak_viewers": deleted_game.peak_viewers,
        "peak_channels": deleted_game.peak_channels,
        "image_url": deleted_game.image_url if deleted_game.image_url else ""
    }

    print(f"\n=== Guardando juego eliminado ===")
    print(f"ID: {game_data['id']}")
    print(f"Nombre: {game_data['game']}")
    print(f"URL de imagen: {game_data['image_url']}")

    # Escribir todos los datos al archivo
    with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)  # Escribir las filas existentes
        if deleted_game.id not in existing_ids:
            writer.writerow(game_data)  # Escribir el nuevo juego eliminado
async def partial_update_game(
    session: AsyncSession,
    game_id: int,
    update_data: dict,
    image: Optional[UploadFile] = None
) -> Optional[GameWithID]:
    """Actualiza parcialmente un juego, incluyendo la posibilidad de actualizar la imagen"""
    
    existing = await session.get(Game, game_id)
    if not existing:
        return None

    # Si hay una nueva imagen, subirla
    if image:
        try:
            image_url = await upload_game_image(image)
            if image_url:
                update_data["image_url"] = image_url
        except Exception as e:
            print(f"Error al subir la imagen: {str(e)}")
            # Continuar con otras actualizaciones incluso si la imagen falla

    # Actualizar los campos proporcionados
    for key, value in update_data.items():
        if hasattr(existing, key):
            setattr(existing, key, value)

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing
