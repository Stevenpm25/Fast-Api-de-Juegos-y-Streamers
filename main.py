from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from typing import Optional, List
import os
import csv
import io
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Models
from models_games import Game, GameWithID, UpdatedGame, GameCreate
from models_streamers import Streamer, StreamerWithID, UpdatedStreamer, StreamerCreate

# Operations
from operations_games import (
    read_all_games, read_one_game, create_game, update_game, delete_game,
    search_games
)
from operations_streamers import (
    read_all_streamers, read_one_streamer, create_streamer, update_streamer,
    delete_streamer, search_streamers
)

app = FastAPI(
    title="API de Games y Streamers",
    description="API para gestionar juegos y streamers",
    version="1.0.0",
    openapi_tags=[{
        "name": "Games",
        "description": "Operaciones con videojuegos"
    }, {
        "name": "Streamers",
        "description": "Operaciones con streamers"
    }]
)


# Configuración de la base de datos
def get_database_url():
    # Usamos la URI proporcionada por Clever Cloud
    uri = os.getenv('POSTGRESQL_ADDON_URI')
    if uri:
        # Reemplazamos el puerto por 50013 y el driver por asyncpg
        return uri.replace("postgresql://", "postgresql+asyncpg://").replace(":5432/", ":50013/")

    # Fallback si no hay URI disponible
    return (
        f"postgresql+asyncpg://{os.getenv('POSTGRESQL_ADDON_USER')}:"
        f"{os.getenv('POSTGRESQL_ADDON_PASSWORD')}@"
        f"{os.getenv('POSTGRESQL_ADDON_HOST')}:"
        f"50013/"  # Puerto fijo 50013
        f"{os.getenv('POSTGRESQL_ADDON_DB')}"
    )


try:
    DATABASE_URL = get_database_url()
    print(f"Conectando a la base de datos...")
    print(f"URL: {DATABASE_URL.split('@')[1].split('/')[0]}")  # Muestra solo host:port

    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

except Exception as e:
    print(f"❌ Error al configurar la base de datos: {str(e)}")
    print("Por favor verifica:")
    print("1. Que tu IP esté autorizada en Clever Cloud")
    print("2. Que las credenciales sean correctas")
    print("3. Que el puerto sea 50013")
    raise

@app.get("/")
def root():
    return {"message": "Hello, Streamers and Videogames Impact API"}
# Dependency
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


# --- Juegos ---
@app.post("/games/import", tags=["Games"])
async def import_games(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        # Verificar tipo de archivo
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV")

        contents = await file.read()
        text = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))

        # Verificar columnas requeridas
        required_columns = {"date", "game", "hours_watched", "peak_viewers", "peak_channels"}
        if not required_columns.issubset(reader.fieldnames):
            raise HTTPException(
                status_code=400,
                detail=f"El CSV debe contener las columnas: {required_columns}"
            )

        inserted = 0
        games = []  # Almacenar temporalmente los juegos
        for row in reader:
            try:
                game = Game(
                    date=row["date"],
                    game=row["game"],
                    hours_watched=int(row["hours_watched"]),
                    peak_viewers=int(row["peak_viewers"]),
                    peak_channels=int(row["peak_channels"]),
                )
                games.append(game)
                inserted += 1
            except (ValueError, KeyError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error en fila {inserted + 1}: {str(e)}"
                )

        # Agregar todos los juegos de una vez
        session.add_all(games)
        await session.commit()

        return {"message": f"Successfully imported {inserted} games"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/games", response_model=List[GameWithID], tags=["Games"])
async def get_all_games(session: AsyncSession = Depends(get_session)):
    return await read_all_games(session)


@app.get("/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def get_game(game_id: int, session: AsyncSession = Depends(get_session)):
    game = await read_one_game(session, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


# Crear juego
@app.post("/games/", response_model=GameWithID, tags=["Games"])
async def create_game(game: GameCreate, session: AsyncSession = Depends(get_session)):
    new_game = Game(**game.dict())
    session.add(new_game)
    await session.commit()
    await session.refresh(new_game)
    return new_game



@app.put("/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def update_existing_game(game_id: int, update: UpdatedGame, session: AsyncSession = Depends(get_session)):
    updated = await update_game(session, game_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")
    return updated


@app.delete("/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def delete_existing_game(game_id: int, session: AsyncSession = Depends(get_session)):
    deleted = await delete_game(session, game_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Game not found")
    return deleted


@app.get("/games/search", response_model=List[GameWithID], tags=["Games"])
async def search_game(
        game_name: Optional[str] = Query(None),
        year: Optional[str] = Query(None),
        session: AsyncSession = Depends(get_session)
):
    return await search_games(session, game_name, year)





# --- Streamers ---
@app.post("/streamers/import", tags=["Streamers"])
async def import_streamers(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        # Verificar tipo de archivo
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV")

        contents = await file.read()
        text = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))

        # Verificar columnas requeridas
        required_columns = {"name", "game", "follower_count", "avg_viewers"}
        if not required_columns.issubset(reader.fieldnames):
            raise HTTPException(
                status_code=400,
                detail=f"El CSV debe contener las columnas: {required_columns}"
            )

        inserted = 0
        streamers = []  # Almacenar temporalmente los streamers
        for row in reader:
            try:
                streamer = Streamer(
                    name=row["name"],
                    game=row["game"],
                    follower_count=int(row["follower_count"]),
                    avg_viewers=int(row["avg_viewers"]),
                )
                streamers.append(streamer)
                inserted += 1
            except (ValueError, KeyError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error en fila {inserted + 1}: {str(e)}"
                )

        # Agregar todos los streamers de una vez
        session.add_all(streamers)
        await session.commit()

        return {"message": f"Successfully imported {inserted} streamers"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/streamers", response_model=List[StreamerWithID], tags=["Streamers"])
async def get_all_streamers(session: AsyncSession = Depends(get_session)):
    return await read_all_streamers(session)


@app.get("/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def get_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    streamer = await read_one_streamer(session, streamer_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


# Crear streamer
@app.post("/streamers", response_model=StreamerWithID, tags=["Streamers"])
async def create_new_streamer(streamer: StreamerCreate, session: AsyncSession = Depends(get_session)):
    return await create_streamer(session, streamer)



@app.put("/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def update_existing_streamer(streamer_id: int, update: UpdatedStreamer,
                                   session: AsyncSession = Depends(get_session)):
    updated = await update_streamer(session, streamer_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return updated


@app.delete("/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def delete_existing_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    deleted = await delete_streamer(session, streamer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return deleted


@app.get("/streamers/search", response_model=List[StreamerWithID], tags=["Streamers"])
async def search_streamer(
        name: Optional[str] = Query(None),
        game: Optional[str] = Query(None),
        session: AsyncSession = Depends(get_session)
):
    return await search_streamers(session, name, game)





# Inicialización de la base de datos
@app.on_event("startup")
async def on_startup():
    try:
        # Verificación de conexión usando text() de SQLAlchemy
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Conexión a la base de datos exitosa")

        # Creación de tablas
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Tablas verificadas/creadas correctamente")
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        print("Por favor verifica:")
        print("1. Que tu IP esté en la lista de permitidos en Clever Cloud")
        print("2. Que el puerto sea 50013")
        print("3. Que las credenciales sean correctas.")
        raise

@app.on_event("shutdown")
async def shutdown_db_connection():
    await engine.dispose()  # Cierra todas las conexiones del pool
    print("✅ Conexiones de la base de datos cerradas")
# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "OK", "message": "API is running"}


# Database Check
@app.get("/db-check", tags=["System"])
async def db_check(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "OK", "message": "Database connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Databas"
                   f"e connection failed: {str(e)}"
        )