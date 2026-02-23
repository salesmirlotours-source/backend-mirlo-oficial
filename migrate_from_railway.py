"""
Script: descarga imágenes pendientes desde Railway y las sube a Cloudinary.
Actualiza las URLs en la base de datos.
"""
import io
import requests
import psycopg2
import cloudinary
import cloudinary.uploader

RAILWAY_BASE = "https://web-production-34ba.up.railway.app"
DB_URL = "postgresql://postgres:cDBhnPzSgNrpKgVVheQHEsAJnOyKWHMk@turntable.proxy.rlwy.net:18046/railway"

cloudinary.config(
    cloud_name="ddtkqinsg",
    api_key="169176496161789",
    api_secret="SYuU2s68nJmRX0nAUQ5fZSvtJ1E",
    secure=True,
)

VIDEO_EXTS = {"mp4", "webm", "mov", "avi"}


def migrate():
    conn = psycopg2.connect(DB_URL, sslmode="require")
    conn.autocommit = True
    cur = conn.cursor()

    stats = {"ok": 0, "skip": 0, "fail": 0}

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
        cur.execute(
            f"SELECT {id_col}, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} LIKE '/uploads/%';"
        )
        rows = cur.fetchall()
        if not rows:
            continue

        print(f"\n{'='*60}")
        print(f"  {table}.{col} — {len(rows)} pendientes")
        print(f"{'='*60}")

        for row_id, old_url in rows:
            download_url = f"{RAILWAY_BASE}{old_url}"

            try:
                resp = requests.get(download_url, timeout=30)
                if resp.status_code != 200:
                    print(f"  [SKIP] ID {row_id}: HTTP {resp.status_code} -> {old_url}")
                    stats["skip"] += 1
                    continue

                # Determinar tipo de recurso
                ext = old_url.rsplit(".", 1)[-1].lower() if "." in old_url else ""
                resource_type = "video" if ext in VIDEO_EXTS else "image"

                # Carpeta en Cloudinary
                parts = old_url.replace("/uploads/", "").rsplit("/", 1)
                folder = parts[0] if len(parts) > 1 else "general"

                # Subir a Cloudinary desde bytes
                result = cloudinary.uploader.upload(
                    io.BytesIO(resp.content),
                    folder=f"mirlotours/{folder}",
                    resource_type=resource_type,
                )
                new_url = result["secure_url"]

                cur.execute(
                    f"UPDATE {table} SET {col} = %s WHERE {id_col} = %s;",
                    (new_url, row_id),
                )
                print(f"  [OK]   ID {row_id}: {old_url} -> {new_url[:80]}...")
                stats["ok"] += 1

            except Exception as e:
                print(f"  [FAIL] ID {row_id}: {e}")
                stats["fail"] += 1

    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  MIGRACIÓN DESDE RAILWAY COMPLETADA")
    print(f"  OK: {stats['ok']} | Skipped: {stats['skip']} | Failed: {stats['fail']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    migrate()
