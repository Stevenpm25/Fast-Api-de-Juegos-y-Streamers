from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models_streamers import *
import os
import csv


async def read_all_streamers(session: AsyncSession) -> List[StreamerWithID]:
    result = await session.execute(select(Streamer))
    return result.scalars().all()



async def read_one_streamer(session: AsyncSession, streamer_id: int) -> Optional[StreamerWithID]:
    return await session.get(Streamer, streamer_id)


async def create_streamer(session: AsyncSession, streamer: StreamerCreate) -> Streamer:
    new_streamer = Streamer(**streamer.dict())
    session.add(new_streamer)
    await session.commit()
    await session.refresh(new_streamer)
    return new_streamer


async def update_streamer(session: AsyncSession, streamer_id: int, update: UpdatedStreamer) -> Optional[StreamerWithID]:
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


def store_deleted_streamer(deleted_streamer: StreamerWithID):
    eliminados_path = "streamerseliminados.csv"

    # Leer datos existentes para evitar duplicados
    existing_ids = set()
    if os.path.exists(eliminados_path):
        with open(eliminados_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            existing_ids = {int(row["id"]) for row in reader if row.get("id")}

    # Si el ID ya existe, no lo agregues de nuevo
    if deleted_streamer.id in existing_ids:
        return

    # Escribir solo campos necesarios (sin followers/total_streams/peak_viewers si no los usas)
    with open(eliminados_path, mode="a", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        if not os.path.exists(eliminados_path):
            writer.writerow(["id", "name", "game", "follower_count", "avg_viewers"])

        writer.writerow([
            deleted_streamer.id,
            deleted_streamer.name,
            deleted_streamer.game,
            deleted_streamer.follower_count,  # Usar el nombre correcto
            deleted_streamer.avg_viewers
        ])
async def delete_streamer(session: AsyncSession, streamer_id: int) -> Optional[StreamerWithID]:
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    # Crear objeto con los campos correctos
    plain_streamer = StreamerWithID(
        id=existing.id,
        name=existing.name,
        game=existing.game,
        follower_count=existing.follower_count,  # Nombre exacto
        avg_viewers=existing.avg_viewers
    )

    store_deleted_streamer(plain_streamer)  # Guardar en CSV (sin duplicados)
    await session.delete(existing)
    await session.commit()
    return plain_streamer
async def search_streamers(
    session: AsyncSession,
    name: str = None,
    game: str = None
) -> List[StreamerWithID]:
    try:
        query = select(Streamer)

        if name:
            search_name = name.lower().strip()
            query = query.where(Streamer.name.ilike(f"%{search_name}%"))

        if game:
            search_game = game.lower().strip()
            query = query.where(Streamer.game.ilike(f"%{search_game}%"))

        result = await session.execute(query)
        streamers = result.scalars().all()
        return [StreamerWithID.model_validate(s) for s in streamers]  # Convertimos a Pydantic
    except Exception as e:
        print(f"Error en search_streamers: {e}")
        return []

# ✅ Operación para importar todos los streamers desde CSV a la base de datos
async def import_streamers_from_csv(session: AsyncSession, csv_path: str = "streamers.csv") -> int:
    inserted = 0
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                streamer = Streamer(
                    id=int(row["id"]),
                    name=row["name"],
                    game=row["game"],
                    follower_count=int(row["follower_count"]),
                    avg_viewers=int(row["avg_viewers"]),
                )
                session.add(streamer)
                inserted += 1
            except Exception as e:
                print(f"Error importing row: {row} => {e}")
    await session.commit()
    return inserted
async def partial_update_streamer(
    session: AsyncSession,
    streamer_id: int,
    update_data: dict
) -> Optional[StreamerWithID]:
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    for key, value in update_data.items():
        if hasattr(existing, key):
            setattr(existing, key, value)

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return StreamerWithID.model_validate(existing)