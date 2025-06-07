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
from image_operations import upload_game_image
from streamer_image_operations import upload_streamer_image

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
    uri = os.getenv('POSTGRESQL_ADDON_URI')
    if uri:
        return uri.replace("postgresql://", "postgresql+asyncpg://").replace(":5432/", ":50013/")

    return (
        f"postgresql+asyncpg://{os.getenv('POSTGRESQL_ADDON_USER')}:"
        f"{os.getenv('POSTGRESQL_ADDON_PASSWORD')}@"
        f"{os.getenv('POSTGRESQL_ADDON_HOST')}:"
        f"50013/"
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
        max_overflow=2,
        pool_recycle=300,
        pool_timeout=30
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


@app.get("/creador", response_class=HTMLResponse)
async def creator_page(request: Request):
    try:
        return templates.TemplateResponse(
            "creator.html",
            {
                "request": request,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        print(f"Error al renderizar la plantilla del creador: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar la página del creador: {str(e)}"
        )


@app.get("/planeacion", response_class=HTMLResponse)
async def planning_page(request: Request):
    try:
        return templates.TemplateResponse(
            "planning.html",
            {
                "request": request,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        print(f"Error al renderizar la plantilla de planificación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar la página de planificación: {str(e)}"
        )


@app.get("/design", response_class=HTMLResponse)
async def design_page(request: Request):
    try:
        return templates.TemplateResponse(
            "design.html",
            {
                "request": request,
                "current_year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        print(f"Error al renderizar la plantilla de diseño: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo cargar la página de diseño: {str(e)}"
        )


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse("analysis.html", {"request": request})


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


@app.post("/api/games", response_model=GameWithID, tags=["Games"])
async def create_new_game(
        game: str = Form(..., description="Nombre del juego"),
        date: str = Form(..., description="Fecha en formato AAAA-MM"),
        hours_watched: int = Form(..., description="Total de horas vistas"),
        peak_viewers: int = Form(..., description="Pico máximo de espectadores"),
        peak_channels: int = Form(..., description="Pico máximo de canales"),
        image: Optional[UploadFile] = File(None, description="Imagen del juego (opcional)"),
        session: AsyncSession = Depends(get_session)
):
    """
    Crear un nuevo juego con imagen opcional.
    La imagen se subirá a Supabase si se proporciona.
    """
    try:
        # Procesar imagen si se proporcionó
        image_url = None
        if image:
            image_url = await upload_game_image(image)

        game_data = GameCreate(
            game=game,
            date=date,
            hours_watched=hours_watched,
            peak_viewers=peak_viewers,
            peak_channels=peak_channels,
            image_url=image_url
        )
        return await create_game(session, game_data)
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Error de validación: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el juego: {str(e)}"
        )


@app.put("/api/games/{game_id}", response_model=GameWithID, tags=["Games"])
async def update_existing_game(
        game_id: int,
        game: str = Form(..., description="Nombre del juego"),
        date: str = Form(..., description="Fecha en formato AAAA-MM"),
        hours_watched: int = Form(..., description="Total de horas vistas"),
        peak_viewers: int = Form(..., description="Pico máximo de espectadores"),
        peak_channels: int = Form(..., description="Pico máximo de canales"),
        image: Optional[UploadFile] = File(None, description="Nueva imagen del juego (opcional)"),
        session: AsyncSession = Depends(get_session)
):
    """
    Actualizar un juego existente con opción de cambiar la imagen.
    Si no se proporciona una nueva imagen, se mantiene la existente.
    """
    try:
        # Verificar si el juego existe
        existing_game = await read_one_game(session, game_id)
        if not existing_game:
            raise HTTPException(status_code=404, detail="Juego no encontrado")

        # Procesar nueva imagen si se proporcionó
        image_url = existing_game.image_url
        if image:
            new_image_url = await upload_game_image(image)
            if new_image_url:
                image_url = new_image_url

        # Crear el objeto de actualización
        update_data = UpdatedGame(
            game=game,
            date=date,
            hours_watched=hours_watched,
            peak_viewers=peak_viewers,
            peak_channels=peak_channels,
            image_url=image_url
        )

        # Actualizar el juego
        updated_game = await update_game(session, game_id, update_data)
        if not updated_game:
            raise HTTPException(status_code=500, detail="Error al actualizar el juego")

        return updated_game

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Error de validación: {str(ve)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el juego: {str(e)}"
        )


@app.patch("/api/games/partial-update/{game_id}", response_model=GameWithID, tags=["Games"])
async def patch_partial_game(
        game_id: int,
        game: Optional[str] = Form(default=None, description="Nuevo nombre del juego",
                                   openapi_extra={"allowEmptyValue": False}),
        date: Optional[str] = Form(default=None, description="Nueva fecha en formato AAAA-MM",
                                   openapi_extra={"allowEmptyValue": False}),
        hours_watched: Optional[int] = Form(default=None, description="Nuevas horas vistas",
                                            openapi_extra={"allowEmptyValue": False}),
        peak_viewers: Optional[int] = Form(default=None, description="Nuevo pico de espectadores",
                                           openapi_extra={"allowEmptyValue": False}),
        peak_channels: Optional[int] = Form(default=None, description="Nuevo pico de canales",
                                            openapi_extra={"allowEmptyValue": False}),
        image: Optional[UploadFile] = Form(default=None, description="Nueva imagen del juego",
                                           openapi_extra={"allowEmptyValue": True}),
        session: AsyncSession = Depends(get_session)
):
    updates = {}

    # Solo incluir los campos que tienen valores válidos y no son valores por defecto
    if game is not None and game.strip() and game.strip().lower() != "string":
        updates["game"] = game
    if date is not None and date.strip() and date.strip().lower() != "string":
        updates["date"] = date
    if hours_watched is not None and hours_watched > 0:  # Ignorar 0
        updates["hours_watched"] = hours_watched
    if peak_viewers is not None and peak_viewers > 0:  # Ignorar 0
        updates["peak_viewers"] = peak_viewers
    if peak_channels is not None and peak_channels > 0:  # Ignorar 0
        updates["peak_channels"] = peak_channels

    # Si se recibe una imagen vacía (Send empty value), establecer image_url a None
    if image == '':
        updates["image_url"] = None

    if not updates and image is None:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos válidos para actualizar")

    try:
        updated = await partial_update_game(session, game_id, updates, image if image != '' else None)
        if not updated:
            raise HTTPException(status_code=404, detail="Juego no encontrado")
        return updated
    except Exception as e:
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


@app.get("/api/games/deleted", tags=["Games"])
async def get_deleted_games():
    eliminados_path = "eliminados.csv"
    if not os.path.exists(eliminados_path):
        return []

    deleted_games = []
    with open(eliminados_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convertir campos numéricos
            row["id"] = int(row["id"])
            row["hours_watched"] = int(row["hours_watched"]) if "hours_watched" in row else 0
            row["peak_viewers"] = int(row["peak_viewers"]) if "peak_viewers" in row else 0
            row["peak_channels"] = int(row["peak_channels"]) if "peak_channels" in row else 0
            # Asegurar que image_url esté presente
            row["image_url"] = row.get("image_url", "")
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
    try:
        eliminados_path = "eliminados.csv"
        if not os.path.exists(eliminados_path):
            raise HTTPException(
                status_code=404,
                detail="No hay juegos eliminados para recuperar"
            )

        # Buscar el juego en el CSV
        recovered = None
        rows = []
        with open(eliminados_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames  # Guardar los nombres de las columnas
            for row in reader:
                if int(row["id"]) == game_id:
                    recovered = row
                else:
                    rows.append(row)

        if not recovered:
            raise HTTPException(
                status_code=404,
                detail=f"Juego con ID {game_id} no encontrado en eliminados"
            )

        # Verificar si el juego ya existe en la base de datos
        existing = await session.get(Game, game_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"El juego con ID {game_id} ya existe en la base de datos"
            )

        # Obtener la URL de la imagen del registro eliminado
        image_url = recovered.get("image_url", "").strip()

        print(f"\n=== Recuperando juego ===")
        print(f"ID: {game_id}")
        print(f"Nombre: {recovered['game']}")
        print(f"URL de imagen: {image_url}")

        # Crear nuevo juego con todos los campos, incluyendo la imagen
        new_game = Game(
            id=int(recovered["id"]),
            date=recovered["date"],
            game=recovered["game"],
            hours_watched=int(recovered["hours_watched"]),
            peak_viewers=int(recovered["peak_viewers"]),
            peak_channels=int(recovered["peak_channels"]),
            image_url=image_url
        )

        session.add(new_game)
        await session.commit()

        # Actualizar el CSV
        with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return {
            "message": f"Juego con ID {game_id} recuperado correctamente",
            "game": {
                "id": new_game.id,
                "date": new_game.date,
                "game": new_game.game,
                "hours_watched": new_game.hours_watched,
                "peak_viewers": new_game.peak_viewers,
                "peak_channels": new_game.peak_channels,
                "image_url": new_game.image_url
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al recuperar el juego: {str(e)}"
        )


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
            # Convertir campos numéricos
            row["id"] = int(row["id"])
            row["follower_count"] = int(row["follower_count"]) if "follower_count" in row else 0
            row["avg_viewers"] = int(row["avg_viewers"]) if "avg_viewers" in row else 0
            # Asegurar que image_url esté presente
            row["image_url"] = row.get("image_url", "")
            deleted_streamers.append(row)

    return deleted_streamers


@app.get("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def get_streamer(streamer_id: int, session: AsyncSession = Depends(get_session)):
    streamer = await read_one_streamer(session, streamer_id)
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


@app.post("/api/streamers", response_model=StreamerWithID, tags=["Streamers"])
async def create_new_streamer(
        name: str = Form(..., description="Nombre del streamer"),
        game: str = Form(..., description="Juego que transmite"),
        follower_count: int = Form(..., description="Número de seguidores"),
        avg_viewers: int = Form(..., description="Promedio de espectadores"),
        image: Optional[UploadFile] = File(None, description="Imagen del streamer (opcional)"),
        session: AsyncSession = Depends(get_session)
):
    """
    Crear un nuevo streamer con imagen opcional.
    La imagen se subirá a Supabase si se proporciona.
    """
    try:
        # Procesar imagen si se proporcionó
        image_url = None
        if image:
            image_url = await upload_streamer_image(image)

        print(f"\n=== Datos del streamer ===")
        print(f"Nombre: {name}")
        print(f"Juego: {game}")
        print(f"Seguidores: {follower_count}")
        print(f"Viewers promedio: {avg_viewers}")
        print(f"URL de imagen: {image_url}")

        streamer_data = StreamerCreate(
            name=name,
            game=game,
            follower_count=follower_count,
            avg_viewers=avg_viewers,
            image_url=image_url
        )

        # Verificar que la tabla existe
        try:
            await session.execute(text("SELECT * FROM streamer LIMIT 1"))
            print("✅ Tabla streamer existe")
        except Exception as e:
            print(f"❌ Error al verificar tabla: {str(e)}")
            raise ValueError(f"Error con la tabla streamer: {str(e)}")

        new_streamer = await create_streamer(session, streamer_data)
        return new_streamer

    except ValueError as ve:
        print(f"❌ Error de validación: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error de validación: {str(ve)}"
        )
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el streamer: {str(e)}"
        )


@app.put("/api/streamers/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def update_existing_streamer(
        streamer_id: int,
        name: Optional[str] = Form(None, description="Nombre del streamer"),
        game: Optional[str] = Form(None, description="Juego que transmite"),
        follower_count: Optional[int] = Form(None, description="Número de seguidores"),
        avg_viewers: Optional[int] = Form(None, description="Promedio de espectadores"),
        image: Optional[UploadFile] = File(None, description="Nueva imagen del streamer (opcional)"),
        session: AsyncSession = Depends(get_session)
):
    try:
        # Crear el objeto UpdatedStreamer con los campos que no son None
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if game is not None:
            update_data["game"] = game
        if follower_count is not None:
            update_data["follower_count"] = follower_count
        if avg_viewers is not None:
            update_data["avg_viewers"] = avg_viewers

        # Si hay imagen, subirla
        if image:
            image_url = await upload_streamer_image(image)
            if image_url:
                update_data["image_url"] = image_url

        update = UpdatedStreamer(**update_data)
        updated_streamer = await update_streamer(session, streamer_id, update)

        if not updated_streamer:
            raise HTTPException(status_code=404, detail="Streamer no encontrado")

        return updated_streamer
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            fieldnames = reader.fieldnames  # Guardar los nombres de las columnas
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

        # Obtener la URL de la imagen del registro eliminado
        image_url = recovered.get("image_url", "").strip()

        print(f"\n=== Recuperando streamer ===")
        print(f"ID: {streamer_id}")
        print(f"Nombre: {recovered['name']}")
        print(f"URL de imagen: {image_url}")

        # Crear nuevo streamer con todos los campos, incluyendo la imagen
        new_streamer = Streamer(
            id=int(recovered["id"]),
            name=recovered["name"],
            game=recovered["game"],
            follower_count=int(recovered["follower_count"]),
            avg_viewers=int(recovered["avg_viewers"]),
            image_url=image_url
        )

        session.add(new_streamer)
        await session.commit()

        # Actualizar el CSV
        with open(eliminados_path, mode="w", newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return {
            "message": f"Streamer con ID {streamer_id} recuperado correctamente",
            "streamer": {
                "id": new_streamer.id,
                "name": new_streamer.name,
                "game": new_streamer.game,
                "follower_count": new_streamer.follower_count,
                "avg_viewers": new_streamer.avg_viewers,
                "image_url": new_streamer.image_url
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al recuperar el streamer: {str(e)}"
        )


@app.patch("/api/streamers/partial-update/{streamer_id}", response_model=StreamerWithID, tags=["Streamers"])
async def patch_partial_streamer(
        streamer_id: int,
        name: Optional[str] = Form(default=None, description="Nuevo nombre del streamer",
                                   openapi_extra={"allowEmptyValue": False}),
        game: Optional[str] = Form(default=None, description="Nuevo juego asociado",
                                   openapi_extra={"allowEmptyValue": False}),
        follower_count: Optional[int] = Form(default=None, description="Nuevo número de seguidores",
                                             openapi_extra={"allowEmptyValue": False}),
        avg_viewers: Optional[int] = Form(default=None, description="Nuevo promedio de espectadores",
                                          openapi_extra={"allowEmptyValue": False}),
        image: Optional[UploadFile] = Form(default=None, description="Nueva imagen del streamer",
                                           openapi_extra={"allowEmptyValue": False}),
        session: AsyncSession = Depends(get_session)
):
    updates = {}

    # Solo incluir los campos que tienen valores válidos y no son valores por defecto
    if name is not None and name.strip() and name.strip().lower() != "string":
        updates["name"] = name
    if game is not None and game.strip() and game.strip().lower() != "string":
        updates["game"] = game
    if follower_count is not None and follower_count > 0:  # Ignorar 0
        updates["follower_count"] = follower_count
    if avg_viewers is not None and avg_viewers > 0:  # Ignorar 0
        updates["avg_viewers"] = avg_viewers

    if not updates and not image:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos válidos para actualizar")

    try:
        updated = await partial_update_streamer(session, streamer_id, updates, image)
        if not updated:
            raise HTTPException(status_code=404, detail="Streamer no encontrado")
        return updated
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el streamer: {str(e)}"
        )


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


@app.get("/api/analysis-data")
async def get_analysis_data():
    data = {
        "games": [
            {"name": "Valorant", "viewers": 6079825, "followers": 2812},
            {"name": "GTA V", "viewers": 9654278, "followers": 35803},
            {"name": "League of Legends", "viewers": 5033750, "followers": 49635},
            {"name": "Counter-Strike", "viewers": 4590554, "followers": 30352},
            {"name": "Minecraft", "viewers": 9996130, "followers": 23958},
            {"name": "Apex Legends", "viewers": 372219, "followers": 21609},
            {"name": "Call of Duty", "viewers": 6648584, "followers": 35670},
            {"name": "Dota 2", "viewers": 3595177, "followers": 4941},
            {"name": "World of Warcraft", "viewers": 1579353, "followers": 13377},
            {"name": "Fortnite", "viewers": 3872409, "followers": 30612}
        ],
        "streamers": [
            {"name": "Rubius", "followers": 6079825, "avg_viewers": 2812},
            {"name": "Asmongold", "followers": 9654278, "avg_viewers": 35803},
            {"name": "Shroud", "followers": 9144183, "avg_viewers": 5298},
            {"name": "xQc", "followers": 5033750, "avg_viewers": 49635},
            {"name": "Pokimane", "followers": 4590554, "avg_viewers": 30352},
            {"name": "Summit1G", "followers": 9996130, "avg_viewers": 23958},
            {"name": "Myth", "followers": 372219, "avg_viewers": 21609},
            {"name": "Tfue", "followers": 6648584, "avg_viewers": 35670},
            {"name": "DrDisrespect", "followers": 3595177, "avg_viewers": 4941},
            {"name": "Ninja", "followers": 1579353, "avg_viewers": 13377}
        ]
    }
    return data