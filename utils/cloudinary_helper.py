import cloudinary
import cloudinary.uploader


def upload_to_cloudinary(file, folder="mirlotours"):
    """
    Sube un archivo (imagen o video) a Cloudinary y devuelve la URL segura.

    Args:
        file: objeto FileStorage de Flask (request.files["file"])
        folder: subcarpeta en Cloudinary (ej: "tours/5/banners")

    Returns:
        str: URL pública del archivo en Cloudinary
    """
    # Detectar si es video por extensión
    ext = ""
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[1].lower()

    video_extensions = {"mp4", "webm", "mov", "avi"}
    resource_type = "video" if ext in video_extensions else "image"

    result = cloudinary.uploader.upload(
        file,
        folder=f"mirlotours/{folder}",
        resource_type=resource_type,
    )

    return result["secure_url"]
