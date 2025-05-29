from fastapi import FastAPI, Depends, Request, HTTPException, Query, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from typing import Optional, List
import os
import csv
import io
import datetime
from dotenv import load_dotenv
from starlette.responses import HTMLResponse

# Cargar variables de entorno
load_dotenv()

# Models
from models_games import Game, GameWithID, UpdatedGame, GameCreate, Game
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

# Configuración de archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

# Dependency
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# Rutas de la interfaz web
@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    try:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        print(f"Error al renderizar la plantilla: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar la página home: {str(e)}"
        )

# Rutas para Games (Web)
@app.get("/games", response_class=HTMLResponse)
async def games_page(
    request: Request,
    game_name: Optional[str] = None,
    year: Optional[str] = None,
    success_msg: Optional[str] = None,
    error_msg: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    try:
        games = await search_games(session, game_name, year) if game_name or year else await read_all_games(session)
        return templates.TemplateResponse(
            "games_list_info.html",
            {
                "request": request,
                "games": games,
                "game_name": game_name,
                "year": year,
                "success_msg": success_msg,
                "error_msg": error_msg,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "games_list_info.html",
            {
                "request": request,
                "games": [],
                "error_msg": f"Error al cargar los juegos: {str(e)}",
                "current_year": datetime.datetime.now().year
            }
        )

@app.get("/games/{game_id}", response_class=HTMLResponse)
async def game_detail_page(
    request: Request,
    game_id: int,
    session: AsyncSession = Depends(get_session)
):
    try:
        game = await read_one_game(session, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Juego no encontrado")

        return templates.TemplateResponse(
            "game_detail.html",
            {
                "request": request,
                "game": game,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/add/game", response_class=HTMLResponse)
async def add_game_page(request: Request):
    return templates.TemplateResponse(
        "add_game_form.html",
        {
            "request": request,
            "current_year": datetime.datetime.now().year
        }
    )

@app.post("/add/game")
async def add_game_submit(
    request: Request,
    game: str = Form(...),
    date: str = Form(...),
    hours_watched: int = Form(...),
    peak_viewers: int = Form(...),
    peak_channels: int = Form(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        # Validar el formato de la fecha
        import re
        if not date or not re.match(r'^\d{4}-\d{2}$', date):
            return RedirectResponse(
                url="/games?error_msg=Formato de fecha inválido. Use AAAA-MM",
                status_code=303
            )

        # Validar valores numéricos
        if hours_watched < 0 or peak_viewers < 0 or peak_channels < 0:
            return RedirectResponse(
                url="/games?error_msg=Los valores numéricos deben ser positivos",
                status_code=303
            )

        new_game = GameCreate(
            game=game,
            date=date,
            hours_watched=hours_watched,
            peak_viewers=peak_viewers,
            peak_channels=peak_channels
        )
        
        created_game = await create_game(session, new_game)
        if created_game:
            return RedirectResponse(
                url="/games?success_msg=¡Juego agregado correctamente!",
                status_code=303
            )
        else:
            return RedirectResponse(
                url="/games?error_msg=Error al crear el juego",
                status_code=303
            )
    except ValueError as ve:
        return RedirectResponse(
            url=f"/games?error_msg=Error de validación: {str(ve)}",
            status_code=303
        )
    except Exception as e:
        print(f"Error al crear juego: {str(e)}")
        return RedirectResponse(
            url=f"/games?error_msg=Error al crear el juego: {str(e)}",
            status_code=303
        )

# API endpoints para Games
@app.post("/games/import", tags=["Games"])
async def import_games(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV")

        contents = await file.read()
        text = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))

        required_columns = {"date", "game", "hours_watched", "peak_viewers", "peak_channels"}
        if not required_columns.issubset(reader.fieldnames):
            raise HTTPException(
                status_code=400,
                detail=f"El CSV debe contener las columnas: {required_columns}"
            )

        inserted = 0
        games = []
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

        session.add_all(games)
        await session.commit()

        return {"message": f"Successfully imported {inserted} games"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/games", response_model=List[GameWithID], tags=["Games"])
async def get_all_games(session: AsyncSession = Depends(get_session)):
    return await read_all_games(session)

@app.get("/api/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def get_game(game_id: int, session: AsyncSession = Depends(get_session)):
    game = await read_one_game(session, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@app.post("/api/games/", response_model=GameWithID, tags=["Games"])
async def create_new_game(game: GameCreate, session: AsyncSession = Depends(get_session)):
    return await create_game(session, game)

@app.put("/api/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def update_existing_game(
    game_id: int,
    update: UpdatedGame,
    session: AsyncSession = Depends(get_session)
):
    try:
        game = await read_one_game(session, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Juego no encontrado")

        update_data = update.model_dump(exclude_unset=True)
        
        # Actualizar solo los campos proporcionados
        for key, value in update_data.items():
            setattr(game, key, value)
        
        session.add(game)
        await session.commit()
        await session.refresh(game)
        
        return game
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el juego: {str(e)}"
        )

@app.delete("/api/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def delete_existing_game(game_id: int, session: AsyncSession = Depends(get_session)):
    try:
        deleted = await delete_game(session, game_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Juego no encontrado")
        return JSONResponse(
            status_code=200,
            content={"message": "¡Juego eliminado correctamente!"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/games/search", response_model=List[GameWithID], tags=["Games"])
async def search_game(
    game_name: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    return await search_games(session, game_name, year)

# API endpoints para Streamers
@app.post("/streamers/import", tags=["Streamers"])
async def import_streamers(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV")

        contents = await file.read()
        text = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))

        required_columns = {"name", "game", "follower_count", "avg_viewers"}
        if not required_columns.issubset(reader.fieldnames):
            raise HTTPException(
                status_code=400,
                detail=f"El CSV debe contener las columnas: {required_columns}"
            )

        inserted = 0
        streamers = []
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

        session.add_all(streamers)
        await session.commit()

        return {"message": f"Successfully imported {inserted} streamers"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/streamers", response_model=List[StreamerWithID], tags=["Streamers"])
async def get_all_streamers(session: AsyncSession = Depends(get_session)):
    return await read_all_streamers(session)

@app.get("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def get_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    streamer = await read_one_streamer(session, streamer_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer

@app.post("/api/streamers", response_model=StreamerWithID, tags=["Streamers"])
async def create_new_streamer(streamer: StreamerCreate, session: AsyncSession = Depends(get_session)):
    return await create_streamer(session, streamer)

@app.put("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def update_existing_streamer(
    streamer_id: int,
    update: UpdatedStreamer,
    session: AsyncSession = Depends(get_session)
):
    updated = await update_streamer(session, streamer_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return updated

@app.delete("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def delete_existing_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    deleted = await delete_streamer(session, streamer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return deleted

@app.get("/api/streamers/search", response_model=List[StreamerWithID], tags=["Streamers"])
async def search_streamer(
    name: Optional[str] = Query(None),
    game: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    return await search_streamers(session, name, game)

# Eventos de inicio y cierre
@app.on_event("startup")
async def on_startup():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Conexión a la base de datos exitosa")

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
    await engine.dispose()
    print("✅ Conexiones de la base de datos cerradas")

# Endpoints de salud
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "OK", "message": "API is running"}

@app.get("/db-check", tags=["System"])
async def db_check(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "OK", "message": "Database connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )