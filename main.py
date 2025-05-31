from fastapi import FastAPI, Depends, Request, HTTPException, Query, UploadFile, File, Form, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from typing import Optional, List, Dict
import os
import csv
import io
import datetime
import random
from dotenv import load_dotenv
from starlette.responses import HTMLResponse
import jinja2

# Cargar variables de entorno
load_dotenv()

# Models
from models_games import Game, GameWithID, UpdatedGame, GameCreate, Game
from models_streamers import Streamer, StreamerWithID, UpdatedStreamer, StreamerCreate

# Operations
from operations_games import (
    read_all_games, read_one_game, create_game, update_game, delete_game,
    search_games, partial_update_game
)
from operations_streamers import (
    read_all_streamers, read_one_streamer, create_streamer, update_streamer,
    delete_streamer, search_streamers, partial_update_streamer, store_deleted_streamer
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

# Configuración de Jinja2
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
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

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
# Rutas para Streamers (Web)
@app.get("/streamers", response_class=HTMLResponse)
async def streamers_page(
    request: Request,
    name: Optional[str] = None,
    game: Optional[str] = None,
    success_msg: Optional[str] = None,
    error_msg: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    try:
        streamers = await search_streamers(session, name, game) if name or game else await read_all_streamers(session)
        return templates.TemplateResponse(
            "streamer_list_info.html",
            {
                "request": request,
                "streamers": streamers,
                "name": name,
                "game": game,
                "success_msg": success_msg,
                "error_msg": error_msg,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "streamer_list_info.html",
            {
                "request": request,
                "streamers": [],
                "error_msg": f"Error al cargar los streamers: {str(e)}",
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

@app.get("/api/games/search", response_model=List[GameWithID], tags=["Games"])
async def search_game(
        game_name: str = Query(None, description="Nombre del juego a buscar"),
        session: AsyncSession = Depends(get_session)
):
    try:
        if game_name is None:
            return []

        games = await search_games(session, game_name)
        return games
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en la búsqueda: {str(e)}"
        )
@app.get("/buscar-id", response_class=HTMLResponse)
async def buscar_id_page(request: Request):
    return templates.TemplateResponse(
        "buscarporid.html",
        {
            "request": request
        }
    )

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
@app.patch("/api/games/partial-update/{game_id}", response_model=GameWithID, tags=["Games"])
async def patch_partial_game(
    game_id: int,
    game: Optional[str] = Query(None, description="Nuevo nombre del juego"),
    date: Optional[str] = Query(None, description="Nueva fecha en formato AAAA-MM-DD"),
    hours_watched: Optional[int] = Query(None, description="Nuevas horas vistas"),
    peak_viewers: Optional[int] = Query(None, description="Nuevo pico de espectadores"),
    peak_channels: Optional[int] = Query(None, description="Nuevo pico de canales"),
    data: Optional[dict] = Body(None),
    session: AsyncSession = Depends(get_session)
):
    updates = {}

    # Procesar parámetros de consulta (query parameters)
    if game is not None:
        updates["game"] = game
    if date is not None:
        updates["date"] = date
    if hours_watched is not None:
        updates["hours_watched"] = hours_watched
    if peak_viewers is not None:
        updates["peak_viewers"] = peak_viewers
    if peak_channels is not None:
        updates["peak_channels"] = peak_channels

    # Procesar datos del cuerpo (JSON)
    if data:
        field = data.get("field")
        value = data.get("value")
        if field and value is not None:
            # Convertir valores numéricos si es necesario
            if field in ["hours_watched", "peak_viewers", "peak_channels"]:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"El valor para {field} debe ser un número entero"
                    )
            updates[field] = value

    if not updates:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar")

    updated = await partial_update_game(session, game_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Juego no encontrado")

    return updated


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


@app.get("/api/games/deleted", tags=["Games"])
async def get_deleted_games():
    eliminados_path = "eliminados.csv"
    if not os.path.exists(eliminados_path):
        return []

    deleted_games = []
    with open(eliminados_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convertir los campos numéricos (que vienen como string del CSV)
            row["id"] = int(row["id"])
            row["hours_watched"] = int(row["hours_watched"])
            row["peak_viewers"] = int(row["peak_viewers"])
            row["peak_channels"] = int(row["peak_channels"])
            deleted_games.append(row)

    return deleted_games

@app.get("/api/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def get_game(game_id: int, session: AsyncSession = Depends(get_session)):
    game = await read_one_game(session, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

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
@app.get("/api/streamers/search", response_model=List[StreamerWithID], tags=["Streamers"])
async def search_streamer(
    name: str = Query(..., description="Nombre del streamer a buscar"),  # Parámetro obligatorio
    session: AsyncSession = Depends(get_session)
):
    try:
        # Limpieza del nombre de búsqueda
        search_name = name.lower().strip()

        # Consulta con filtro insensible a mayúsculas/minúsculas
        query = select(Streamer).where(Streamer.name.ilike(f"%{search_name}%"))
        result = await session.execute(query)
        streamers = result.scalars().all()

        if not streamers:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron streamers con ese nombre"
            )

        return [StreamerWithID.model_validate(s) for s in streamers]
    except HTTPException:
        raise  # Re-lanza errores HTTP personalizados
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en la búsqueda: {str(e)}"
        )
@app.post("/api/games/recover/{game_id}", tags=["Games"])
async def recover_deleted_game(game_id: int, session: AsyncSession = Depends(get_session)):
    eliminados_path = "eliminados.csv"
    if not os.path.exists(eliminados_path):
        raise HTTPException(status_code=404, detail="No hay eliminados para recuperar")

    recovered = None
    rows = []
    with open(eliminados_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row["id"]) == game_id:
                recovered = row
            else:
                rows.append(row)

    if not recovered:
        raise HTTPException(status_code=404, detail="Juego no encontrado en eliminados")

    # Insertar de nuevo en la base de datos
    new_game = Game(
        id=int(recovered["id"]),
        date=recovered["date"],
        game=recovered["game"],
        hours_watched=int(recovered["hours_watched"]),
        peak_viewers=int(recovered["peak_viewers"]),
        peak_channels=int(recovered["peak_channels"]),
    )
    session.add(new_game)
    await session.commit()

    # Actualizar el archivo eliminados.csv removiendo el recuperado
    with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "date", "game", "hours_watched", "peak_viewers", "peak_channels"])
        writer.writeheader()
        writer.writerows(rows)

    return {"message": f"Juego con ID {game_id} recuperado correctamente"}

@app.get("/api/streamers", response_model=List[StreamerWithID], tags=["Streamers"])
async def get_all_streamers(session: AsyncSession = Depends(get_session)):
    return await read_all_streamers(session)

@app.delete("/api/streamers/{streamer_id}", tags=["Streamers"])
async def delete_existing_streamer(
    streamer_id: int,
    session: AsyncSession = Depends(get_session)
):
    try:
        deleted = await delete_streamer(session, streamer_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Streamer no encontrado")

        plain_streamer = StreamerWithID.model_validate(deleted)
        store_deleted_streamer(plain_streamer)

        return JSONResponse(
            status_code=200,
            content={
                "message": "¡Streamer eliminado correctamente!",
                "deleted_streamer": plain_streamer.dict()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar el streamer: {str(e)}"
        )
@app.get("/api/streamers/deleted", tags=["Streamers"])
async def get_deleted_streamers():
    eliminados_path = "streamerseliminados.csv"
    if not os.path.exists(eliminados_path):
        return []

    deleted_streamers = []
    with open(eliminados_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convertir campos numéricos (si es necesario)
            row["id"] = int(row["id"])
            row["followers"] = int(row["followers"]) if "followers" in row else 0
            row["avg_viewers"] = int(row["avg_viewers"]) if "avg_viewers" in row else 0
            row["total_streams"] = int(row["total_streams"]) if "total_streams" in row else 0
            row["peak_viewers"] = int(row["peak_viewers"]) if "peak_viewers" in row else 0
            deleted_streamers.append(row)

    return deleted_streamers
@app.get("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def get_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    streamer = await read_one_streamer(session, streamer_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer

@app.post("/api/streamers", response_model=StreamerWithID, tags=["Streamers"])
async def create_new_streamer(streamer: StreamerCreate, session: AsyncSession = Depends(get_session)):
    return await create_streamer(session, streamer)
@app.post("/api/streamers/recover/{streamer_id}", tags=["Streamers"])
@app.post("/api/streamers/recover/{streamer_id}", tags=["Streamers"])
async def recover_deleted_streamer(
        streamer_id: int,
        session: AsyncSession = Depends(get_session)
):
    try:
        eliminados_path = "streamerseliminados.csv"

        # Verificar si el archivo existe
        if not os.path.exists(eliminados_path):
            raise HTTPException(
                status_code=404,
                detail="No hay streamers eliminados para recuperar"
            )

        # Buscar el streamer en el CSV
        recovered = None
        rows = []
        with open(eliminados_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["id"]) == streamer_id:
                    recovered = row
                else:
                    rows.append(row)

        if not recovered:
            raise HTTPException(
                status_code=404,
                detail=f"Streamer con ID {streamer_id} no encontrado en eliminados"
            )

        # Verificar si el streamer ya existe en la base de datos
        existing = await session.get(Streamer, streamer_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"El streamer con ID {streamer_id} ya existe en la base de datos"
            )

        # Crear nuevo streamer (asegurar tipos de datos)
        new_streamer = Streamer(
            id=int(recovered["id"]),
            name=recovered["name"],
            game=recovered["game"],
            follower_count=int(recovered["follower_count"]),
            avg_viewers=int(recovered["avg_viewers"])
        )

        session.add(new_streamer)
        await session.commit()

        # Actualizar el CSV
        with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return {"message": f"Streamer con ID {streamer_id} recuperado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al recuperar el streamer: {str(e)}"
        )
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


from fastapi.responses import JSONResponse


@app.get("/api/games/search", response_model=List[GameWithID], tags=["Games"])
async def search_game(
        game_name: str = Query(None, description="Nombre del juego a buscar"),
        session: AsyncSession = Depends(get_session)
):
    try:
        if not game_name:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un nombre de juego para buscar"
            )

        games = await search_games(session, game_name)
        if not games:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron juegos con ese nombre"
            )

        return games
    except HTTPException:
        raise  # Re-lanza excepciones HTTP personalizadas
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en la búsqueda: {str(e)}"
        )
@app.patch("/api/streamers/partial-update/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def patch_partial_streamer(
    streamer_id: int,
    name: Optional[str] = Query(None, description="Nuevo nombre del streamer"),
    game: Optional[str] = Query(None, description="Nuevo juego asociado"),
    followers: Optional[int] = Query(None, description="Nuevo número de seguidores"),
    avg_viewers: Optional[int] = Query(None, description="Nuevo promedio de espectadores"),
    total_streams: Optional[int] = Query(None, description="Nuevo total de streams"),
    peak_viewers: Optional[int] = Query(None, description="Nuevo pico de espectadores"),
    session: AsyncSession = Depends(get_session)
):
    updates = {}

    if name is not None:
        updates["name"] = name
    if game is not None:
        updates["game"] = game
    if followers is not None:
        updates["followers"] = followers
    if avg_viewers is not None:
        updates["avg_viewers"] = avg_viewers
    if total_streams is not None:
        updates["total_streams"] = total_streams
    if peak_viewers is not None:
        updates["peak_viewers"] = peak_viewers

    if not updates:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar")

    updated = await partial_update_streamer(session, streamer_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Streamer no encontrado")

    return updated
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

# Rutas para AI Chat
@app.get("/ai-chat", response_class=HTMLResponse, tags=["AI"])
async def ai_chat_page(request: Request):
    try:
        return templates.TemplateResponse(
            "ai_chat.html",
            {
                "request": request,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        print(f"Error al renderizar la plantilla de AI Chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar la página de AI Chat: {str(e)}"
        )

@app.post("/api/ai-chat", response_model=Dict[str, str], tags=["AI"])
async def ai_chat_api(message: Dict[str, str] = Body(...)):
    try:
        user_message = message.get("message", "").lower()

        # Respuestas predefinidas para preguntas comunes de código
        code_responses = {
            "python": "```python\n# Ejemplo de código Python\ndef saludar(nombre):\n    return f'¡Hola, {nombre}!'\n\n# Uso de la función\nprint(saludar('Usuario'))\n```",
            "javascript": "```javascript\n// Ejemplo de código JavaScript\nfunction saludar(nombre) {\n    return `¡Hola, ${nombre}!`;\n}\n\n// Uso de la función\nconsole.log(saludar('Usuario'));\n```",
            "html": "```html\n<!-- Ejemplo de código HTML -->\n<!DOCTYPE html>\n<html>\n<head>\n    <title>Mi Página</title>\n</head>\n<body>\n    <h1>¡Hola, Mundo!</h1>\n    <p>Esta es una página HTML de ejemplo.</p>\n</body>\n</html>\n```",
            "css": "```css\n/* Ejemplo de código CSS */\nbody {\n    font-family: Arial, sans-serif;\n    background-color: #f0f0f0;\n    color: #333;\n}\n\nh1 {\n    color: #0066cc;\n    text-align: center;\n}\n```",
            "java": "```java\n// Ejemplo de código Java\npublic class Saludo {\n    public static void main(String[] args) {\n        System.out.println(\"¡Hola, Mundo!\");\n    }\n}\n```",
            "c#": "```csharp\n// Ejemplo de código C#\nusing System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine(\"¡Hola, Mundo!\");\n    }\n}\n```",
            "fastapi": "```python\n# Ejemplo de código FastAPI\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/\")\nasync def root():\n    return {\"message\": \"¡Hola, Mundo!\"}\n\n@app.get(\"/items/{item_id}\")\nasync def read_item(item_id: int):\n    return {\"item_id\": item_id}\n```",
            "sql": "```sql\n-- Ejemplo de código SQL\nCREATE TABLE usuarios (\n    id INT PRIMARY KEY,\n    nombre VARCHAR(100),\n    email VARCHAR(100),\n    fecha_registro DATE\n);\n\nINSERT INTO usuarios (id, nombre, email, fecha_registro)\nVALUES (1, 'Juan Pérez', 'juan@ejemplo.com', '2023-01-15');\n\nSELECT * FROM usuarios WHERE id = 1;\n```"
        }

        # Respuestas generales
        general_responses = [
            "Puedo ayudarte a generar código en varios lenguajes. ¿En qué lenguaje estás interesado?",
            "Para generar código, especifica el lenguaje y lo que quieres hacer. Por ejemplo: 'Muéstrame código en Python para leer un archivo'.",
            "¿Necesitas ayuda con algún lenguaje de programación específico?",
            "Estoy aquí para ayudarte con ejemplos de código. ¿Qué tipo de funcionalidad necesitas implementar?"
        ]

        # Buscar coincidencias en las preguntas de código
        for key, response in code_responses.items():
            if key in user_message:
                return {"response": f"Aquí tienes un ejemplo de código en {key.capitalize()}:\n\n{response}"}

        # Respuestas para preguntas específicas
        if "hola" in user_message or "saludos" in user_message:
            return {"response": "¡Hola! Soy tu asistente de código. ¿En qué puedo ayudarte hoy?"}
        elif "gracias" in user_message:
            return {"response": "¡De nada! Estoy aquí para ayudarte. ¿Hay algo más en lo que pueda asistirte?"}
        elif "ayuda" in user_message:
            return {"response": "Puedo ayudarte a generar código en varios lenguajes como Python, JavaScript, HTML, CSS, Java, C#, FastAPI y SQL. Solo pregúntame por el lenguaje que necesitas."}
        elif "generar" in user_message and "código" in user_message:
            return {"response": "Para generar código, por favor especifica el lenguaje de programación y la funcionalidad que necesitas. Por ejemplo: 'Genera código en Python para una calculadora simple'."}
        elif "función" in user_message or "funcion" in user_message:
            return {"response": "```python\n# Ejemplo de una función en Python\ndef calcular_area(base, altura):\n    \"\"\"Calcula el área de un rectángulo\"\"\"\n    return base * altura\n\n# Uso de la función\narea = calcular_area(5, 3)\nprint(f'El área es: {area}')\n```"}
        elif "clase" in user_message:
            return {"response": "```python\n# Ejemplo de una clase en Python\nclass Persona:\n    def __init__(self, nombre, edad):\n        self.nombre = nombre\n        self.edad = edad\n    \n    def saludar(self):\n        return f'Hola, mi nombre es {self.nombre} y tengo {self.edad} años.'\n\n# Crear una instancia de la clase\npersona = Persona('Ana', 25)\nprint(persona.saludar())\n```"}
        elif "api" in user_message or "rest" in user_message:
            return {"response": "```python\n# Ejemplo de una API REST con FastAPI\nfrom fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass Item(BaseModel):\n    name: str\n    price: float\n\nitems = []\n\n@app.post('/items/')\nasync def create_item(item: Item):\n    items.append(item)\n    return item\n\n@app.get('/items/')\nasync def read_items():\n    return items\n```"}

        # Si no hay coincidencias específicas, devolver una respuesta general aleatoria
        return {"response": random.choice(general_responses)}

    except Exception as e:
        print(f"Error en AI Chat API: {str(e)}")
        return {"response": "Lo siento, ha ocurrido un error al procesar tu solicitud."}

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
