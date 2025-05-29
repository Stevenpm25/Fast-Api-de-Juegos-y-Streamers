from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models_games import Game, GameWithID, UpdatedGame,GameCreate, Game
import csv


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

    await session.delete(existing)
    await session.commit()
    return existing


async def search_games(session: AsyncSession, game_name: Optional[str] = None, year: Optional[str] = None) -> List[GameWithID]:
    query = select(Game)

    if game_name:
        query = query.where(Game.game.ilike(f"%{game_name}%"))

    if year:
        query = query.where(Game.date.startswith(year))

    result = await session.execute(query)  # Aquí está el cambio de exec a execute
    return result.scalars().all()  # También agregamos scalars() para obtener los resultados correctamente


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