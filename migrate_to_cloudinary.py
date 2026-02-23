"""
Script de migración: sube todas las imágenes locales (/uploads/...) a Cloudinary
y actualiza las URLs en la base de datos.
"""
import os
import psycopg2
import cloudinary
import cloudinary.uploader

# ── Configuración ──
DB_URL = "postgresql://postgres:cDBhnPzSgNrpKgVVheQHEsAJnOyKWHMk@turntable.proxy.rlwy.net:18046/railway"
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

cloudinary.config(
    cloud_name="ddtkqinsg",
    api_key="169176496161789",
    api_secret="SYuU2s68nJmRX0nAUQ5fZSvtJ1E",
    secure=True,
)

VIDEO_EXTS = {"mp4", "webm", "mov", "avi"}


def upload_file(local_path, folder):
    """Sube un archivo a Cloudinary y retorna la URL."""
    ext = local_path.rsplit(".", 1)[-1].lower() if "." in local_path else ""
    resource_type = "video" if ext in VIDEO_EXTS else "image"

    result = cloudinary.uploader.upload(
        local_path,
        folder=f"mirlotours/{folder}",
        resource_type=resource_type,
    )
    return result["secure_url"]


def migrate():
    conn = psycopg2.connect(DB_URL, sslmode="require")
    conn.autocommit = True
    cur = conn.cursor()

    stats = {"ok": 0, "skip": 0, "fail": 0}

    # ── Tablas a migrar: (tabla, columna_url, columna_id) ──
    migrations = [
        ("travel.tours", "foto_portada", "id"),
        ("travel.galerias", "foto_url", "id"),
        ("travel.guias", "foto_url", "id"),
        ("travel.tour_banners", "media_url", "id"),
        ("travel.tour_banners", "poster_url", "id"),
        ("travel.portadas_home", "imagen_url", "id"),
        ("travel.categorias", "imagen_url", "id"),
        ("travel.tour_ubicaciones", "imagen_url", "id"),
    ]

    for table, col, id_col in migrations:
        cur.execute(f"SELECT {id_col}, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} LIKE '/uploads/%';")
        rows = cur.fetchall()

        if not rows:
            continue

        print(f"\n{'='*60}")
        print(f"  {table}.{col} — {len(rows)} registros por migrar")
        print(f"{'='*60}")

        for row_id, old_url in rows:
            # Convertir URL de BD a ruta local: /uploads/tours/3/portada.jpg -> uploads/tours/3/portada.jpg
            relative = old_url.lstrip("/")
            local_path = os.path.join(UPLOADS_DIR, "..", relative)
            local_path = os.path.normpath(local_path)

            if not os.path.exists(local_path):
                print(f"  [SKIP] ID {row_id}: archivo no encontrado -> {local_path}")
                stats["skip"] += 1
                continue

            # Determinar carpeta en Cloudinary
            # /uploads/tours/3/portada.jpg -> tours/3
            parts = old_url.replace("/uploads/", "").rsplit("/", 1)
            folder = parts[0] if len(parts) > 1 else "general"

            try:
                new_url = upload_file(local_path, folder)
                cur.execute(f"UPDATE {table} SET {col} = %s WHERE {id_col} = %s;", (new_url, row_id))
                print(f"  [OK]   ID {row_id}: {old_url} -> {new_url[:80]}...")
                stats["ok"] += 1
            except Exception as e:
                print(f"  [FAIL] ID {row_id}: {e}")
                stats["fail"] += 1

    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  MIGRACIÓN COMPLETADA")
    print(f"  OK: {stats['ok']} | Skipped: {stats['skip']} | Failed: {stats['fail']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    migrate()
