from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models_streamers import *
from fastapi import UploadFile
import os
import csv
from streamer_image_operations import upload_streamer_image


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
    existing_rows = []
    fieldnames = ["id", "name", "game", "follower_count", "avg_viewers", "image_url"]

    if os.path.exists(eliminados_path):
        with open(eliminados_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("id") and int(row["id"]) != deleted_streamer.id:
                    existing_rows.append(row)
                    existing_ids.add(int(row["id"]))

    # Preparar los datos del streamer eliminado
    streamer_data = { #hola
        "id": deleted_streamer.id,
        "name": deleted_streamer.name,
        "game": deleted_streamer.game,
        "follower_count": deleted_streamer.follower_count,
        "avg_viewers": deleted_streamer.avg_viewers,
        "image_url": deleted_streamer.image_url if deleted_streamer.image_url else ""
    }

    print(f"\n=== Guardando streamer eliminado ===")
    print(f"ID: {streamer_data['id']}")
    print(f"Nombre: {streamer_data['name']}")
    print(f"URL de imagen: {streamer_data['image_url']}")

    # Escribir todos los datos al archivo
    with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)  # Escribir las filas existentes
        if deleted_streamer.id not in existing_ids:
            writer.writerow(streamer_data)  # Escribir el nuevo streamer eliminado

async def delete_streamer(session: AsyncSession, streamer_id: int) -> Optional[StreamerWithID]:
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    # Crear objeto con los campos correctos, incluyendo image_url
    plain_streamer = StreamerWithID(
        id=existing.id,
        name=existing.name,
        game=existing.game,
        follower_count=existing.follower_count,
        avg_viewers=existing.avg_viewers,
        image_url=existing.image_url
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
    update_data: dict,
    image: Optional[UploadFile] = None
) -> Optional[StreamerWithID]:
    """Actualiza parcialmente un streamer, incluyendo la posibilidad de actualizar la imagen"""
    from streamer_image_operations import upload_streamer_image  # Importar aquí para evitar dependencia circular
    
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    # Si hay una nueva imagen, subirla
    if image:
        try:
            image_url = await upload_streamer_image(image)
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
    return StreamerWithID.model_validate(existing)

async def create_streamer_with_image(
    session: AsyncSession, 
    streamer: StreamerCreate, 
    image: Optional[UploadFile] = None
) -> Streamer:
    """Crea un nuevo streamer con imagen opcional"""
    streamer_data = streamer.dict()
    
    if image:
        image_url = await upload_streamer_image(image)
        if image_url:
            streamer_data["image_url"] = image_url
    
    new_streamer = Streamer(**streamer_data)
    session.add(new_streamer)
    await session.commit()
    await session.refresh(new_streamer)
    return new_streamer

async def update_streamer_with_image(
    session: AsyncSession, 
    streamer_id: int, 
    update: UpdatedStreamer,
    image: Optional[UploadFile] = None
) -> Optional[StreamerWithID]:
    """Actualiza un streamer existente con imagen opcional"""
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    # Actualizar campos normales
    update_data = update.model_dump(exclude_unset=True)
    
    # Si hay una nueva imagen, subirla
    if image:
        image_url = await upload_streamer_image(image)
        if image_url:
            update_data["image_url"] = image_url

    for key, value in update_data.items():
        setattr(existing, key, value)

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing