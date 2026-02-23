import io
import time
import cloudinary
import cloudinary.uploader
from PIL import Image

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB (límite free de Cloudinary)
MAX_IMAGE_WIDTH = 3000  # px máximo de ancho para redimensionar
JPEG_QUALITY = 85
CHUNK_SIZE = 6 * 1024 * 1024  # 6 MB por chunk para videos grandes


def _compress_image(file_bytes, filename):
    """
    Comprime una imagen si supera MAX_IMAGE_SIZE.
    Redimensiona a MAX_IMAGE_WIDTH y convierte a JPEG quality 85.
    """
    if len(file_bytes) <= MAX_IMAGE_SIZE:
        return file_bytes

    print(f"  [Cloudinary] Imagen grande ({len(file_bytes)/1024/1024:.1f}MB), comprimiendo...")
    img = Image.open(io.BytesIO(file_bytes))

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if img.width > MAX_IMAGE_WIDTH:
        ratio = MAX_IMAGE_WIDTH / img.width
        new_size = (MAX_IMAGE_WIDTH, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    buf.seek(0)
    compressed = buf.read()
    print(f"  [Cloudinary] Comprimida a {len(compressed)/1024:.0f}KB")
    return compressed


def upload_to_cloudinary(file, folder="mirlotours"):
    """
    Sube un archivo (imagen o video) a Cloudinary y devuelve la URL segura.
    - Imágenes >10MB se comprimen automáticamente.
    - Videos: Cloudinary los convierte automáticamente a formato optimizado.
    - Usa eager transforms para que Cloudinary comprima videos en la nube.
    """
    ext = ""
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[1].lower()

    video_extensions = {"mp4", "webm", "mov", "avi"}
    resource_type = "video" if ext in video_extensions else "image"

    file_bytes = file.read()
    size_mb = len(file_bytes) / 1024 / 1024

    print(f"  [Cloudinary] Subiendo {file.filename} ({size_mb:.1f}MB) como {resource_type} a {folder}...")
    start = time.time()

    if resource_type == "image":
        file_bytes = _compress_image(file_bytes, file.filename)
        result = cloudinary.uploader.upload(
            io.BytesIO(file_bytes),
            folder=f"mirlotours/{folder}",
            resource_type="image",
            timeout=120,
        )
    else:
        # Videos: subir con eager transform para que Cloudinary
        # genere una versión optimizada (720p, calidad auto)
        result = cloudinary.uploader.upload_large(
            io.BytesIO(file_bytes),
            folder=f"mirlotours/{folder}",
            resource_type="video",
            chunk_size=CHUNK_SIZE,
            timeout=300,
            eager=[{"quality": "auto", "fetch_format": "mp4"}],
            eager_async=True,
        )

    elapsed = time.time() - start
    print(f"  [Cloudinary] OK en {elapsed:.1f}s -> {result['secure_url'][:80]}...")

    return result["secure_url"]
