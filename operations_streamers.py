from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models_streamers import *
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


async def delete_streamer(session: AsyncSession, streamer_id: int) -> Optional[StreamerWithID]:
    existing = await session.get(Streamer, streamer_id)
    if not existing:
        return None

    await session.delete(existing)
    await session.commit()
    return existing


async def search_streamers(session: AsyncSession, name: str = None, game: str = None) -> List[StreamerWithID]:
    query = select(Streamer)

    if name:
        query = query.where(Streamer.name.ilike(f"%{name}%"))

    if game:
        query = query.where(Streamer.game.ilike(f"%{game}%"))

    result = await session.exec(query)
    return result.all()


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
