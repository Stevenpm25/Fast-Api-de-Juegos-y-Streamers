import os
import uuid
from fastapi import UploadFile
from dotenv import load_dotenv
from supabase.client import create_client, Client

load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
SUPABASE_BUCKET = "games_images"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar configurados en el archivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def upload_game_image(file: UploadFile) -> str:
    """
    Sube una imagen a Supabase y retorna la URL pública.
    Retorna None si hay algún error.
    """
    try:
        print("\n=== Configuración de Supabase ===")
        print(f"URL: {SUPABASE_URL}")
        print(f"Bucket: {SUPABASE_BUCKET}")
        print(f"Key configurada: {'Sí' if SUPABASE_KEY else 'No'}")
        
        print("\n=== Información del archivo ===")
        print(f"Nombre: {file.filename}")
        print(f"Tipo: {file.content_type}")
        
        if not file.content_type.startswith("image/"):
            print(f"❌ Error: El archivo no es una imagen. Tipo de contenido: {file.content_type}")
            return None

        print("\n=== Preparando archivo para subida ===")
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        print(f"Nombre generado: {new_filename}")

        content = await file.read()
        print(f"Tamaño: {len(content)} bytes")
        
        print("\n=== Subiendo archivo ===")
        res = supabase.storage.from_(SUPABASE_BUCKET).upload(
            new_filename,
            content,
            {"content-type": file.content_type}
        )
        print(f"✅ Archivo subido exitosamente")

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(new_filename)
        print(f"✅ URL pública generada: {public_url}")
        
        return public_url

    except Exception as e:
        print(f"\n❌ Error en el proceso:")
        print(f"Tipo: {type(e)}")
        print(f"Mensaje: {str(e)}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None 