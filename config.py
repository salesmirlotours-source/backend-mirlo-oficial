# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # carga .env si existe

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # URL de tu PostgreSQL en Railway
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:SEniCbiQObIIcHRTNxMBxvdFwkmkkfhY@turntable.proxy.rlwy.net:59803/railway"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")

    # Para que SQLAlchemy apunte por defecto al schema travel
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "options": "-csearch_path=travel"
        }
    }

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # 📸 Configuración de uploads (fotos en el mismo servidor)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
