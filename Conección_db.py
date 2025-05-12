import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Cargar variables de entorno desde utils/.env
env_path = Path(__file__).parent.parent /"PyCharmPr"/ ".env"
load_dotenv(env_path)

# Verificar variables críticas antes de continuar
required_vars = [
    'POSTGRESQL_ADDON_USER',
    'POSTGRESQL_ADDON_PASSWORD',
    'POSTGRESQL_ADDON_HOST',
    'POSTGRESQL_ADDON_PORT',
    'POSTGRESQL_ADDON_DB'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Faltan variables de entorno críticas: {missing_vars}")

# Configuración de la conexión
CLEVER_DB = (
    f"postgresql+asyncpg://{os.getenv('POSTGRESQL_ADDON_USER')}:"
    f"{os.getenv('POSTGRESQL_ADDON_PASSWORD')}@"
    f"{os.getenv('POSTGRESQL_ADDON_HOST')}:"
    f"{os.getenv('POSTGRESQL_ADDON_PORT')}/"
    f"{os.getenv('POSTGRESQL_ADDON_DB')}"
)

# SQLite como fallback (opcional)
DATABASE_URL = "sqlite+aiosqlite:///petsdb.db"

# Motor de base de datos principal
try:
    engine: AsyncEngine = create_async_engine(CLEVER_DB, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception as e:
    print(f"Error al conectar a PostgreSQL: {e}")
    # Fallback a SQLite si hay error
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Inicializa la estructura de la base de datos."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session():
    """Provee una sesión asíncrona para operaciones en la DB."""
    async with async_session() as session:
        yield session