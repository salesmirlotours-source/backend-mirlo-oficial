# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # carga .env si existe

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # URL de tu PostgreSQL en Railway
    _db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:cDBhnPzSgNrpKgVVheQHEsAJnOyKWHMk@turntable.proxy.rlwy.net:18046/railway"
    )
    # Agregar sslmode si no está presente
    if "sslmode" not in _db_url:
        _db_url = _db_url + "?sslmode=require"
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Para que SQLAlchemy apunte por defecto al schema travel
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "options": "-csearch_path=travel",
            "sslmode": "require"
        },
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # 📸 Configuración de uploads (fotos en el mismo servidor)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
