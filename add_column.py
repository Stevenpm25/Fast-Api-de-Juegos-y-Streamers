from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def get_database_url():
    uri = os.getenv('POSTGRESQL_ADDON_URI')
    if uri:
        # Reemplazar el puerto 5432 por 50013
        return uri.replace(":5432/", ":50013/")
    return (
        f"postgresql://{os.getenv('POSTGRESQL_ADDON_USER')}:"
        f"{os.getenv('POSTGRESQL_ADDON_PASSWORD')}@"
        f"{os.getenv('POSTGRESQL_ADDON_HOST')}:"
        f"50013/"
        f"{os.getenv('POSTGRESQL_ADDON_DB')}"
    )

try:
    # Crear el engine
    database_url = get_database_url()
    print(f"Conectando a: {database_url.split('@')[1]}")  # Solo mostrar host:port/db
    engine = create_engine(database_url)
    
    # Conectar y ejecutar la alteración
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE streamer ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"))
        print("✅ Columna image_url agregada exitosamente")
        
except Exception as e:
    print(f"❌ Error al agregar la columna: {str(e)}") 