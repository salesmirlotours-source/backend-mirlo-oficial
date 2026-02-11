# routes/admin_routes.py
import os
from datetime import date
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from flask import current_app # Para saber donde está la carpeta de tu app
from extensions import db
from models import (
    Usuario,
    Tour,
    FechaTour,
    Itinerario,
    Galeria,
    TourSeccion,
    TourIncluye,
    Guia,
    TourGuia,
    Comentario,
    Reserva,
    ReservaEstado,
    PagoEstado,
    FechaEstado,
    SeccionTipo,
    IncluyeTipo,
    ComentarioEstado,
    TourBanner, MediaTipo,
    TourUbicacion,
    Categoria,
    ConsultaTour
)
from sqlalchemy import func # <--- AGREGA ESTO AL INICIO DE admin_routes.py
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --------------- Helpers de auth / admin -------------------

def _require_admin():
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    if not user or user.rol not in ("admin", "super_admin"):
        return None, (jsonify({"message": "No autorizado"}), 403)
    return user, None


# --------------- Helper para uploads -----------------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ================== UPLOAD DE ARCHIVOS GENÉRICO =====================

@admin_bp.post("/upload")
@jwt_required()
def upload_file():
    """
    Sube una imagen al servidor y devuelve la URL para guardarla en BD.
    Requiere ser admin.
    """
    _, error = _require_admin()
    if error:
        return error

    if "file" not in request.files:
        return jsonify({"message": "No se envió ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "Nombre de archivo vacío"}), 400

    if not allowed_file(file.filename):
        return jsonify({"message": "Tipo de archivo no permitido"}), 400

    filename = secure_filename(file.filename)

    # opcional subcarpeta: tours, guias, etc.
    folder = request.form.get("folder", "").strip()
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    if folder:
        upload_folder = os.path.join(upload_folder, folder)
        os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # construir URL pública
    url_path = f"/uploads/{folder}/{filename}" if folder else f"/uploads/{filename}"
    url_path = url_path.replace("//", "/")

    return jsonify({
        "message": "Archivo subido correctamente",
        "url": url_path
    }), 201


# ================== CATEGORÍAS (ADMIN) =====================

@admin_bp.get("/categorias")
@jwt_required()
def admin_list_categorias():
    """Lista todas las categorías (activas e inactivas)"""
    _, error = _require_admin()
    if error:
        return error

    categorias = Categoria.query.order_by(Categoria.orden).all()
    return jsonify([{
        **c.to_dict(),
        "total_tours": len([t for t in c.tours if t.activo])
    } for c in categorias])


@admin_bp.post("/categorias")
@jwt_required()
def admin_create_categoria():
    """Crear una nueva categoría"""
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}

    if not data.get("nombre"):
        return jsonify({"message": "El nombre es obligatorio"}), 400

    # Generar slug si no se envía
    slug = data.get("slug") or data["nombre"].lower().replace(" ", "-")

    # Verificar que el slug no exista
    if Categoria.query.filter_by(slug=slug).first():
        return jsonify({"message": "Ya existe una categoría con ese slug"}), 400

    categoria = Categoria(
        nombre=data["nombre"],
        slug=slug,
        descripcion=data.get("descripcion"),
        imagen_url=data.get("imagen_url"),
        icono=data.get("icono"),
        orden=data.get("orden", 0),
        activo=data.get("activo", True)
    )

    db.session.add(categoria)
    db.session.commit()

    return jsonify({
        "message": "Categoría creada",
        "categoria": categoria.to_dict()
    }), 201


@admin_bp.put("/categorias/<int:categoria_id>")
@jwt_required()
def admin_update_categoria(categoria_id):
    """Editar una categoría"""
    _, error = _require_admin()
    if error:
        return error

    categoria = Categoria.query.get(categoria_id)
    if not categoria:
        return jsonify({"message": "Categoría no encontrada"}), 404

    data = request.get_json() or {}

    if "nombre" in data:
        categoria.nombre = data["nombre"]
    if "slug" in data:
        # Verificar que el nuevo slug no exista en otra categoría
        existing = Categoria.query.filter_by(slug=data["slug"]).first()
        if existing and existing.id != categoria_id:
            return jsonify({"message": "Ya existe otra categoría con ese slug"}), 400
        categoria.slug = data["slug"]
    if "descripcion" in data:
        categoria.descripcion = data["descripcion"]
    if "imagen_url" in data:
        categoria.imagen_url = data["imagen_url"]
    if "icono" in data:
        categoria.icono = data["icono"]
    if "orden" in data:
        categoria.orden = data["orden"]
    if "activo" in data:
        categoria.activo = data["activo"]

    db.session.commit()

    return jsonify({
        "message": "Categoría actualizada",
        "categoria": categoria.to_dict()
    })


@admin_bp.delete("/categorias/<int:categoria_id>")
@jwt_required()
def admin_delete_categoria(categoria_id):
    """Eliminar una categoría (los tours quedan sin categoría)"""
    _, error = _require_admin()
    if error:
        return error

    categoria = Categoria.query.get(categoria_id)
    if not categoria:
        return jsonify({"message": "Categoría no encontrada"}), 404

    # Los tours quedarán con categoria_id = NULL por el ON DELETE SET NULL
    db.session.delete(categoria)
    db.session.commit()

    return jsonify({"message": "Categoría eliminada"})


@admin_bp.patch("/tours/<int:tour_id>/categoria")
@jwt_required()
def admin_set_tour_categoria(tour_id):
    """Asignar o cambiar la categoría de un tour"""
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}
    categoria_id = data.get("categoria_id")

    if categoria_id:
        categoria = Categoria.query.get(categoria_id)
        if not categoria:
            return jsonify({"message": "Categoría no encontrada"}), 404
        tour.categoria_id = categoria_id
    else:
        tour.categoria_id = None  # Quitar categoría

    db.session.commit()

    return jsonify({
        "message": "Categoría del tour actualizada",
        "tour_id": tour.id,
        "categoria": tour.categoria.to_dict() if tour.categoria else None
    })


# ================== DASHBOARD ADMIN =====================
@admin_bp.get("/dashboard/resumen")
@jwt_required()
def admin_dashboard_resumen():
    _, error = _require_admin()
    if error: return error

    # 1. TOTALES GENERALES (Fila superior)
    tours_activos = Tour.query.filter_by(activo=True).count()
    total_reservas = Reserva.query.count()
    comentarios_pendientes = Comentario.query.filter_by(estado=ComentarioEstado.PENDIENTE).count()
    pagos_pendientes = Reserva.query.filter_by(estado_pago=PagoEstado.PENDIENTE).count()

    # 2. DESGLOSE DE RESERVAS (Para la tarjeta inferior izquierda)
    reservas_estado = {
        "pre_reserva": Reserva.query.filter_by(estado_reserva=ReservaEstado.PRE_RESERVA).count(),
        "confirmada": Reserva.query.filter_by(estado_reserva=ReservaEstado.CONFIRMADA).count(),
        "cancelada_cliente": Reserva.query.filter_by(estado_reserva=ReservaEstado.CANCELADA_CLIENTE).count(),
        "cancelada_operador": Reserva.query.filter_by(estado_reserva=ReservaEstado.CANCELADA_OPERADOR).count(),
    }

    # 3. INGRESOS REALES (Opcional si quieres mantenerlo)
    ingresos_totales = db.session.query(func.sum(Reserva.monto_total))\
        .filter(Reserva.estado_pago == PagoEstado.PAGADO)\
        .scalar() or 0

    return jsonify({
        # FILA 1: TARJETAS SUPERIORES
        "tours_activos": tours_activos,
        "total_reservas": total_reservas,
        "comentarios_pendientes": comentarios_pendientes,
        "pagos_pendientes": pagos_pendientes,
        "ingresos_totales": float(ingresos_totales),

        # FILA 2: DETALLE DE ESTADOS
        "reservas_estado": reservas_estado
    })
# ================== TOURS =====================

@admin_bp.get("/tours")
@jwt_required()
def admin_list_tours():
    _, error = _require_admin()
    if error:
        return error

    tours = Tour.query.order_by(Tour.created_at.desc()).all()
    return jsonify([t.to_detail_dict() for t in tours])


@admin_bp.post("/tours")
@jwt_required()
def admin_create_tour():
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    required = ["nombre", "slug", "pais", "duracion_dias"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    if Tour.query.filter_by(slug=data["slug"]).first():
        return jsonify({"message": "Ya existe un tour con ese slug"}), 400

    nivel_actividad = data.get("nivel_actividad")
    if nivel_actividad:
        nivel_actividad = nivel_actividad.lower()

    tour = Tour(
        nombre=data["nombre"],
        slug=data["slug"],
        pais=data["pais"],
        duracion_dias=int(data["duracion_dias"]),
        nivel_actividad=nivel_actividad,
        precio_pp=data.get("precio_pp"),
        moneda=data.get("moneda", "USD"),
        banner_url=data.get("banner_url"),
        foto_portada=data.get("foto_portada"),  # ⭐ NUEVO
        descripcion_corta=data.get("descripcion_corta"),
        descripcion_larga=data.get("descripcion_larga"),
        ruta_resumida=data.get("ruta_resumida"),
        guia_principal_id=data.get("guia_principal_id"),
        activo=data.get("activo", True),
        orden_destacado=data.get("orden_destacado")
    )

    db.session.add(tour)
    db.session.commit()

    return jsonify({"message": "Tour creado", "tour": tour.to_detail_dict()}), 201


@admin_bp.get("/tours/<int:tour_id>")
@jwt_required()
def admin_get_tour(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    return jsonify(tour.to_detail_dict())


@admin_bp.put("/tours/<int:tour_id>")
@jwt_required()
def admin_update_tour(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}

    for field in [
        "nombre", "slug", "pais", "duracion_dias", "nivel_actividad",
        "precio_pp", "moneda", "banner_url",
        "foto_portada",
        "descripcion_corta",
        "descripcion_larga", "ruta_resumida", "guia_principal_id",
        "activo", "orden_destacado",
        "categoria_id"  # Para asignar categoría
    ]:
        if field in data:
            setattr(tour, field, data[field])

    db.session.commit()
    return jsonify({"message": "Tour actualizado", "tour": tour.to_detail_dict()})


# =====================================================
# NUEVO ENDPOINT: Subir foto de portada
# =====================================================

@admin_bp.post("/tours/<int:tour_id>/portada")
@jwt_required()
def admin_upload_portada(tour_id):
    """
    Sube una foto de portada para el tour.
    Soporta multipart/form-data con campo 'file'.
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    if "file" not in request.files:
        return jsonify({"message": "No se envió ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "Nombre de archivo vacío"}), 400

    if not allowed_file(file.filename):
        return jsonify({"message": "Tipo de archivo no permitido"}), 400

    filename = secure_filename(file.filename)
    
    # Renombrar a "portada.ext" para evitar acumulación de archivos
    ext = filename.rsplit(".", 1)[1].lower()
    filename = f"portada.{ext}"

    # Carpeta: uploads/tours/<tour_id>/
    folder = os.path.join("tours", str(tour.id))
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Actualizar el tour con la URL de la portada
    foto_url = f"/uploads/{folder}/{filename}".replace("//", "/")
    tour.foto_portada = foto_url
    db.session.commit()

    return jsonify({
        "message": "Foto de portada actualizada",
        "foto_portada": foto_url,
        "tour": tour.to_card_dict()
    }), 200


@admin_bp.delete("/tours/<int:tour_id>")
@jwt_required()
def admin_delete_tour(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    tour.activo = False
    db.session.commit()

    return jsonify({"message": "Tour desactivado"})


@admin_bp.delete("/tours/<int:tour_id>/permanente")
@jwt_required()
def admin_delete_tour_permanente(tour_id):
    """
    Elimina un tour PERMANENTEMENTE de la base de datos.
    CUIDADO: Esta accion no se puede deshacer.
    Elimina: comentarios, reservas, fechas, itinerarios, galeria, secciones, incluye, banners, ubicaciones.
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    # Guardar nombre para el mensaje
    nombre_tour = tour.nombre

    try:
        # Eliminar manualmente las relaciones que no tienen CASCADE en la BD
        # 1. Eliminar comentarios del tour
        Comentario.query.filter_by(tour_id=tour_id).delete()

        # 2. Eliminar reservas del tour
        Reserva.query.filter_by(tour_id=tour_id).delete()

        # 3. Eliminar fechas del tour (las reservas ya fueron eliminadas)
        FechaTour.query.filter_by(tour_id=tour_id).delete()

        # 4. Eliminar itinerarios
        Itinerario.query.filter_by(tour_id=tour_id).delete()

        # 5. Eliminar galeria
        Galeria.query.filter_by(tour_id=tour_id).delete()

        # 6. Eliminar secciones
        TourSeccion.query.filter_by(tour_id=tour_id).delete()

        # 7. Eliminar incluye/no incluye
        TourIncluye.query.filter_by(tour_id=tour_id).delete()

        # 8. Eliminar guias asociados
        TourGuia.query.filter_by(tour_id=tour_id).delete()

        # 9. Eliminar banners
        TourBanner.query.filter_by(tour_id=tour_id).delete()

        # 10. Eliminar ubicaciones
        TourUbicacion.query.filter_by(tour_id=tour_id).delete()

        # Finalmente eliminar el tour
        db.session.delete(tour)
        db.session.commit()

        return jsonify({
            "message": f"Tour '{nombre_tour}' eliminado permanentemente",
            "deleted_id": tour_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": f"Error al eliminar tour: {str(e)}"
        }), 500


@admin_bp.post("/tours/<int:tour_id>/fechas")
@jwt_required()
def admin_create_fecha(tour_id):
    # --- CHIVATO DE DEBUG ---
    print("!!! EJECUTANDO CODIGO NUEVO !!!")
    data = request.get_json() or {}
    estado_recibido = data.get("estado", "NO_ENVIADO")
    print(f"!!! ESTADO RECIBIDO DE POSTMAN: {estado_recibido}")
    # ------------------------

    _, error = _require_admin()
    if error: return error

    tour = Tour.query.get(tour_id)
    if not tour: return jsonify({"message": "Tour no encontrado"}), 404

    # required = ... (resto de tu código) ...
    required = ["fecha_inicio", "fecha_fin", "cupos_totales"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    # --- CORRECCIÓN FORZADA ---
    estado_input = data.get("estado", "abierta")
    
    # FORZAR A STRING Y MINÚSCULAS MANUALMENTE
    if estado_input:
        estado_input = str(estado_input).lower().strip()
    else:
        estado_input = "abierta"
        
    print(f"!!! ESTADO QUE SE ENVIARÁ A LA BD: {estado_input}") 
    # ---------------------------

    fecha = FechaTour(
        tour_id=tour.id,
        fecha_inicio=date.fromisoformat(data["fecha_inicio"]),
        fecha_fin=date.fromisoformat(data["fecha_fin"]),
        cupos_totales=int(data["cupos_totales"]),
        cupos_ocupados=data.get("cupos_ocupados", 0),
        estado=estado_input, # <--- Usamos la variable minúscula
        notas=data.get("notas")
    )

    db.session.add(fecha)
    db.session.commit()

    return jsonify({"message": "Fecha creada", "fecha": fecha.to_dict()}), 201



@admin_bp.put("/fechas/<int:fecha_id>")
@jwt_required()
def admin_update_fecha(fecha_id):
    _, error = _require_admin()
    if error:
        return error

    fecha = FechaTour.query.get(fecha_id)
    if not fecha:
        return jsonify({"message": "Fecha no encontrada"}), 404

    data = request.get_json() or {}

    if "fecha_inicio" in data:
        fecha.fecha_inicio = date.fromisoformat(data["fecha_inicio"])
    if "fecha_fin" in data:
        fecha.fecha_fin = date.fromisoformat(data["fecha_fin"])
    if "cupos_totales" in data:
        fecha.cupos_totales = int(data["cupos_totales"])
    if "cupos_ocupados" in data:
        fecha.cupos_ocupados = int(data["cupos_ocupados"])
    if "estado" in data:
        fecha.estado = data["estado"]
    if "notas" in data:
        fecha.notas = data["notas"]

    db.session.commit()
    return jsonify({"message": "Fecha actualizada", "fecha": fecha.to_dict()})


@admin_bp.delete("/fechas/<int:fecha_id>")
@jwt_required()
def admin_delete_fecha(fecha_id):
    _, error = _require_admin()
    if error:
        return error

    fecha = FechaTour.query.get(fecha_id)
    if not fecha:
        return jsonify({"message": "Fecha no encontrada"}), 404

    db.session.delete(fecha)
    db.session.commit()
    return jsonify({"message": "Fecha eliminada"})


# ================== ITINERARIO =====================

@admin_bp.post("/tours/<int:tour_id>/itinerarios")
@jwt_required()
def admin_create_itinerario(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}
    required = ["orden_dia", "titulo_dia", "descripcion_dia"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    orden_dia = int(data["orden_dia"])

    existente = Itinerario.query.filter_by(
        tour_id=tour.id,
        orden_dia=orden_dia
    ).first()

    if existente:
        return (
            jsonify({
                "message": "Ya existe un día de itinerario con ese orden para este tour",
                "tour_id": tour.id,
                "orden_dia": orden_dia,
            }),
            400,
        )

    item = Itinerario(
        tour_id=tour.id,
        orden_dia=orden_dia,
        titulo_dia=data["titulo_dia"],
        descripcion_dia=data["descripcion_dia"],
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({"message": "Día de itinerario creado", "itinerario": item.to_dict()}), 201


@admin_bp.put("/itinerarios/<int:item_id>")
@jwt_required()
def admin_update_itinerario(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = Itinerario.query.get(item_id)
    if not item:
        return jsonify({"message": "Itinerario no encontrado"}), 404

    data = request.get_json() or {}
    if "orden_dia" in data:
        item.orden_dia = int(data["orden_dia"])
    if "titulo_dia" in data:
        item.titulo_dia = data["titulo_dia"]
    if "descripcion_dia" in data:
        item.descripcion_dia = data["descripcion_dia"]

    db.session.commit()
    return jsonify({"message": "Itinerario actualizado", "itinerario": item.to_dict()})


@admin_bp.delete("/itinerarios/<int:item_id>")
@jwt_required()
def admin_delete_itinerario(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = Itinerario.query.get(item_id)
    if not item:
        return jsonify({"message": "Itinerario no encontrado"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Itinerario eliminado"})


# ================== GALERÍA (por TOUR, con soporte form-data) =====================

@admin_bp.post("/tours/<int:tour_id>/galeria")
@jwt_required()
def admin_create_galeria(tour_id):
    """
    Agrega una imagen a la galería de un tour.

    Soporta:
    1) multipart/form-data:
        - file: archivo de imagen
        - categoria (opcional)
        - descripcion (opcional)
        - orden (opcional)

    2) JSON:
        {
          "foto_url": "/uploads/lo-que-sea.jpg",
          "categoria": "...",
          "descripcion": "...",
          "orden": 1
        }
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    foto_url = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"message": "Nombre de archivo vacío"}), 400

        if not allowed_file(file.filename):
            return jsonify({"message": "Tipo de archivo no permitido"}), 400

        filename = secure_filename(file.filename)

        # carpeta: uploads/tours/<tour_id>/
        folder = os.path.join("tours", str(tour.id))
        upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        foto_url = f"/uploads/{folder}/{filename}".replace("//", "/")

        data = request.form
    else:
        data = request.get_json() or {}
        foto_url = data.get("foto_url")

    if not foto_url:
        return jsonify({"message": "Debe enviarse un archivo 'file' o un 'foto_url'"}), 400

    categoria = data.get("categoria")
    descripcion = data.get("descripcion")
    orden = data.get("orden")

    item = Galeria(
        tour_id=tour.id,
        categoria=categoria,
        foto_url=foto_url,
        descripcion=descripcion,
        orden=orden,
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({"message": "Imagen agregada a galería", "galeria": item.to_dict()}), 201


@admin_bp.delete("/galeria/<int:item_id>")
@jwt_required()
def admin_delete_galeria(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = Galeria.query.get(item_id)
    if not item:
        return jsonify({"message": "Elemento de galería no encontrado"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Elemento de galería eliminado"})


# ================== SECCIONES (info práctica / políticas) =====================

@admin_bp.post("/tours/<int:tour_id>/secciones")
@jwt_required()
def admin_create_seccion(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}
    required = ["tipo", "titulo", "contenido"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    item = TourSeccion(
        tour_id=tour.id,
        tipo=data["tipo"],
        titulo=data["titulo"],
        contenido=data["contenido"],
        orden=data.get("orden"),
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({"message": "Sección creada", "seccion": item.to_dict()}), 201


@admin_bp.put("/secciones/<int:item_id>")
@jwt_required()
def admin_update_seccion(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = TourSeccion.query.get(item_id)
    if not item:
        return jsonify({"message": "Sección no encontrada"}), 404

    data = request.get_json() or {}
    if "tipo" in data:
        item.tipo = data["tipo"]
    if "titulo" in data:
        item.titulo = data["titulo"]
    if "contenido" in data:
        item.contenido = data["contenido"]
    if "orden" in data:
        item.orden = data["orden"]

    db.session.commit()
    return jsonify({"message": "Sección actualizada", "seccion": item.to_dict()})


@admin_bp.delete("/secciones/<int:item_id>")
@jwt_required()
def admin_delete_seccion(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = TourSeccion.query.get(item_id)
    if not item:
        return jsonify({"message": "Sección no encontrada"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Sección eliminada"})


# ================== INCLUYE / NO INCLUYE =====================

@admin_bp.post("/tours/<int:tour_id>/incluye")
@jwt_required()
def admin_create_incluye(tour_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}
    required = ["tipo", "descripcion"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    tipo_raw = str(data.get("tipo", "")).strip()
    tipo_normalizado = tipo_raw.lower()

    if tipo_normalizado == "incluye":
        tipo_enum = IncluyeTipo.INCLUYE
    elif tipo_normalizado in ("no_incluye", "no incluye", "no-incluye"):
        tipo_enum = IncluyeTipo.NO_INCLUYE
    else:
        return (
            jsonify({
                "message": "Tipo inválido. Debe ser 'incluye' o 'no_incluye'",
                "valor_recibido": tipo_raw,
            }),
            400,
        )

    item = TourIncluye(
        tour_id=tour.id,
        tipo=tipo_enum,
        descripcion=data["descripcion"],
        orden=data.get("orden"),
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({"message": "Ítem creado", "item": item.to_dict()}), 201


# ================== GUÍAS (con soporte form-data para foto) =====================

@admin_bp.get("/guias")
@jwt_required()
def admin_list_guias():
    _, error = _require_admin()
    if error:
        return error

    guias = Guia.query.order_by(Guia.nombre.asc()).all()
    return jsonify([
        {
            "id": g.id,
            "nombre": g.nombre,
            "foto_url": g.foto_url,
            "bio": g.bio,
            "especialidad": g.especialidad,
            "idiomas": g.idiomas,
            "pais_base": g.pais_base,
            "activo": g.activo,
        }
        for g in guias
    ])


@admin_bp.post("/guias")
@jwt_required()
def admin_create_guia():
    """
    Crea un guía.

    Soporta:
    1) multipart/form-data:
        - file: foto del guía (opcional)
        - nombre (obligatorio)
        - bio, especialidad, idiomas, pais_base, redes_sociales, activo (opcionales)

    2) JSON:
        {
          "nombre": "...",
          "foto_url": "/uploads/guias/...",
          ...
        }
    """
    _, error = _require_admin()
    if error:
        return error

    foto_url = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"message": "Nombre de archivo vacío"}), 400

        if not allowed_file(file.filename):
            return jsonify({"message": "Tipo de archivo no permitido"}), 400

        filename = secure_filename(file.filename)

        folder = "guias"
        upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        foto_url = f"/uploads/{folder}/{filename}".replace("//", "/")

        data = request.form
    else:
        data = request.get_json() or {}
        foto_url = data.get("foto_url")

    if "nombre" not in data or not data["nombre"]:
        return jsonify({"message": "nombre es obligatorio"}), 400

    guia = Guia(
        nombre=data["nombre"],
        foto_url=foto_url,
        bio=data.get("bio"),
        especialidad=data.get("especialidad"),
        idiomas=data.get("idiomas"),
        pais_base=data.get("pais_base"),
        redes_sociales=data.get("redes_sociales"),
        activo=data.get("activo", True),
    )
    db.session.add(guia)
    db.session.commit()

    return jsonify({"message": "Guía creado", "id": guia.id, "guia": {
        "id": guia.id,
        "nombre": guia.nombre,
        "foto_url": guia.foto_url,
        "bio": guia.bio,
        "especialidad": guia.especialidad,
        "idiomas": guia.idiomas,
        "pais_base": guia.pais_base,
        "redes_sociales": guia.redes_sociales,
        "activo": guia.activo,
    }}), 201


@admin_bp.put("/guias/<int:guia_id>")
@jwt_required()
def admin_update_guia(guia_id):
    """
    Actualiza datos de un guía.

    Soporta:
    - multipart/form-data (para cambiar foto y/o campos)
    - JSON
    """
    _, error = _require_admin()
    if error:
        return error

    guia = Guia.query.get(guia_id)
    if not guia:
        return jsonify({"message": "Guía no encontrado"}), 404

    foto_url = guia.foto_url  # valor actual por defecto

    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"message": "Nombre de archivo vacío"}), 400

        if not allowed_file(file.filename):
            return jsonify({"message": "Tipo de archivo no permitido"}), 400

        filename = secure_filename(file.filename)

        folder = "guias"
        upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        foto_url = f"/uploads/{folder}/{filename}".replace("//", "/")

        data = request.form
    else:
        data = request.get_json() or {}

    # actualizar campos
    for field in ["nombre", "bio", "especialidad", "idiomas", "pais_base", "redes_sociales", "activo"]:
        if field in data:
            setattr(guia, field, data[field])

    guia.foto_url = foto_url

    db.session.commit()
    return jsonify({"message": "Guía actualizado", "guia": {
        "id": guia.id,
        "nombre": guia.nombre,
        "foto_url": guia.foto_url,
        "bio": guia.bio,
        "especialidad": guia.especialidad,
        "idiomas": guia.idiomas,
        "pais_base": guia.pais_base,
        "redes_sociales": guia.redes_sociales,
        "activo": guia.activo,
    }})


@admin_bp.delete("/guias/<int:guia_id>")
@jwt_required()
def admin_delete_guia(guia_id):
    _, error = _require_admin()
    if error:
        return error

    guia = Guia.query.get(guia_id)
    if not guia:
        return jsonify({"message": "Guía no encontrado"}), 404

    guia.activo = False
    db.session.commit()
    return jsonify({"message": "Guía desactivado"})


@admin_bp.post("/tours/<int:tour_id>/guias/<int:guia_id>")
@jwt_required()
def admin_add_guia_to_tour(tour_id, guia_id):
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    guia = Guia.query.get(guia_id)
    if not tour or not guia:
        return jsonify({"message": "Tour o guía no encontrados"}), 404

    if TourGuia.query.filter_by(tour_id=tour.id, guia_id=guia.id).first():
        return jsonify({"message": "El guía ya está asociado a este tour"}), 400

    tg = TourGuia(tour_id=tour.id, guia_id=guia.id, rol="Guía")
    db.session.add(tg)
    db.session.commit()
    return jsonify({"message": "Guía asociado al tour"}), 201


@admin_bp.delete("/tours/<int:tour_id>/guias/<int:guia_id>")
@jwt_required()
def admin_remove_guia_from_tour(tour_id, guia_id):
    _, error = _require_admin()
    if error:
        return error

    tg = TourGuia.query.filter_by(tour_id=tour_id, guia_id=guia_id).first()
    if not tg:
        return jsonify({"message": "Asociación no encontrada"}), 404

    db.session.delete(tg)
    db.session.commit()
    return jsonify({"message": "Guía removido del tour"})


# ================== RESERVAS (ADMIN) =====================
# =====================================================
# REEMPLAZA EN admin_routes.py - Endpoint de listar reservas
# =====================================================

@admin_bp.get("/reservas")
@jwt_required()
def admin_list_reservas():
    """
    Lista todas las reservas con datos completos del cliente y tour.
    Soporta filtros: estado_reserva, estado_pago, tour_id, usuario_id
    """
    _, error = _require_admin()
    if error:
        return error

    estado_reserva_str = request.args.get("estado_reserva")
    estado_pago_str = request.args.get("estado_pago")
    tour_id = request.args.get("tour_id")
    usuario_id = request.args.get("usuario_id")

    q = Reserva.query

    if estado_reserva_str:
        estado_reserva_str = estado_reserva_str.strip().lower()
        mapping_reserva = {
            "pre_reserva": ReservaEstado.PRE_RESERVA,
            "confirmada": ReservaEstado.CONFIRMADA,
            "cancelada_cliente": ReservaEstado.CANCELADA_CLIENTE,
            "cancelada_operador": ReservaEstado.CANCELADA_OPERADOR,
        }
        estado_reserva_enum = mapping_reserva.get(estado_reserva_str)
        if estado_reserva_enum:
            q = q.filter_by(estado_reserva=estado_reserva_enum)

    if estado_pago_str:
        estado_pago_str = estado_pago_str.strip().lower()
        mapping_pago = {
            "pendiente": PagoEstado.PENDIENTE,
            "pagado": PagoEstado.PAGADO,
            "reembolso_parcial": PagoEstado.REEMBOLSO_PARCIAL,
            "reembolso_total": PagoEstado.REEMBOLSO_TOTAL,
            "sin_reembolso": PagoEstado.SIN_REEMBOLSO,
        }
        estado_pago_enum = mapping_pago.get(estado_pago_str)
        if estado_pago_enum:
            q = q.filter_by(estado_pago=estado_pago_enum)

    if tour_id:
        q = q.filter_by(tour_id=int(tour_id))
    if usuario_id:
        q = q.filter_by(usuario_id=int(usuario_id))

    reservas = q.order_by(Reserva.created_at.desc()).all()

    # Construir respuesta con datos completos
    resultado = []
    for r in reservas:
        # Obtener datos del usuario
        usuario = Usuario.query.get(r.usuario_id)
        # Obtener datos del tour
        tour = Tour.query.get(r.tour_id)
        # Obtener datos de la fecha
        fecha = FechaTour.query.get(r.fecha_tour_id) if r.fecha_tour_id else None

        resultado.append({
            "id": r.id,
            "usuario_id": r.usuario_id,
            "tour_id": r.tour_id,
            "fecha_tour_id": r.fecha_tour_id,
            "numero_personas": r.numero_personas,
            "estado_reserva": r.estado_reserva.value if hasattr(r.estado_reserva, 'value') else r.estado_reserva,
            "estado_pago": r.estado_pago.value if hasattr(r.estado_pago, 'value') else r.estado_pago,
            "monto_total": float(r.monto_total) if r.monto_total else 0,
            "moneda": r.moneda or "USD",
            "metodo_pago_externo": r.metodo_pago_externo,
            "referencia_pago": r.referencia_pago,
            "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else None,
            "comentarios_cliente": r.comentarios_cliente,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            
            # ⭐ DATOS DEL CLIENTE
            "usuario": {
                "id": usuario.id if usuario else None,
                "nombre": usuario.nombre if usuario else None,
                "apellido": getattr(usuario, 'apellido', None) if usuario else None,
                "email": usuario.email if usuario else None,
                "telefono": getattr(usuario, 'telefono', None) if usuario else None,
            } if usuario else None,
            
            # Alias para compatibilidad
            "cliente_nombre": usuario.nombre if usuario else None,
            "cliente_email": usuario.email if usuario else None,
            "cliente_telefono": getattr(usuario, 'telefono', None) if usuario else None,
            
            # ⭐ DATOS DEL TOUR
            "tour": {
                "id": tour.id if tour else None,
                "nombre": tour.nombre if tour else None,
                "slug": tour.slug if tour else None,
                "pais": tour.pais if tour else None,
            } if tour else None,
            
            # Alias para compatibilidad
            "tour_nombre": tour.nombre if tour else None,
            
            # ⭐ DATOS DE LA FECHA
            "fecha_inicio": fecha.fecha_inicio.isoformat() if fecha and fecha.fecha_inicio else None,
            "fecha_fin": fecha.fecha_fin.isoformat() if fecha and fecha.fecha_fin else None,
        })

    return jsonify(resultado)

@admin_bp.post("/reservas")
@jwt_required()
def admin_create_reserva():
    """
    Crea una reserva desde el panel de administración.
    """
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    required = ["usuario_id", "tour_id", "fecha_tour_id", "numero_personas"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    try:
        usuario_id = int(data["usuario_id"])
        tour_id = int(data["tour_id"])
        fecha_tour_id = int(data["fecha_tour_id"])
        numero_personas = int(data["numero_personas"])
    except (ValueError, TypeError):
        return jsonify({"message": "usuario_id, tour_id, fecha_tour_id y numero_personas deben ser enteros"}), 400

    if numero_personas < 1:
        return jsonify({"message": "numero_personas debe ser al menos 1"}), 400

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    fecha = FechaTour.query.filter_by(id=fecha_tour_id, tour_id=tour.id).first()
    if not fecha:
        return jsonify({"message": "La fecha seleccionada no pertenece a este tour"}), 400

    if fecha.cupos_ocupados + numero_personas > fecha.cupos_totales:
        return jsonify({"message": "No hay cupos suficientes para esta fecha"}), 400

    estado_reserva_str = data.get("estado_reserva", "pre_reserva").strip().lower()
    mapping_reserva = {
        "pre_reserva": ReservaEstado.PRE_RESERVA,
        "confirmada": ReservaEstado.CONFIRMADA,
        "cancelada_cliente": ReservaEstado.CANCELADA_CLIENTE,
        "cancelada_operador": ReservaEstado.CANCELADA_OPERADOR,
    }
    estado_reserva_enum = mapping_reserva.get(estado_reserva_str, ReservaEstado.PRE_RESERVA)

    estado_pago_str = data.get("estado_pago", "pendiente").strip().lower()
    mapping_pago = {
        "pendiente": PagoEstado.PENDIENTE,
        "pagado": PagoEstado.PAGADO,
        "reembolso_parcial": PagoEstado.REEMBOLSO_PARCIAL,
        "reembolso_total": PagoEstado.REEMBOLSO_TOTAL,
        "sin_reembolso": PagoEstado.SIN_REEMBOLSO,
    }
    estado_pago_enum = mapping_pago.get(estado_pago_str, PagoEstado.PENDIENTE)

    reserva = Reserva(
        usuario_id=usuario.id,
        tour_id=tour.id,
        fecha_tour_id=fecha.id,
        numero_personas=numero_personas,
        estado_reserva=estado_reserva_enum,
        estado_pago=estado_pago_enum,
        monto_total=data.get("monto_total"),
        moneda=data.get("moneda", "USD"),
        comentarios_cliente=data.get("comentarios_cliente"),
        comentarios_internos=data.get("comentarios_internos"),
    )

    fecha.cupos_ocupados += numero_personas

    db.session.add(reserva)
    db.session.commit()

    return jsonify({
        "message": "Reserva creada correctamente",
        "reserva": reserva.to_dict_public(),
    }), 201


@admin_bp.get("/reservas/pre-reservas")
@jwt_required()
def listar_pre_reservas():
    _, error = _require_admin()
    if error:
        return error

    reservas = Reserva.query.filter_by(
        estado_reserva=ReservaEstado.PRE_RESERVA
    ).order_by(Reserva.created_at.asc()).all()

    return jsonify([r.to_dict_public() for r in reservas])


@admin_bp.patch("/reservas/<int:reserva_id>/confirmar")
@jwt_required()
def confirmar_reserva(reserva_id):
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    metodo_pago = data.get("metodo_pago_externo")
    referencia = data.get("referencia_pago")
    fecha_pago = data.get("fecha_pago")

    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404

    reserva.estado_reserva = ReservaEstado.CONFIRMADA
    reserva.estado_pago = PagoEstado.PAGADO
    reserva.metodo_pago_externo = metodo_pago
    reserva.referencia_pago = referencia
    if fecha_pago:
        reserva.fecha_pago = date.fromisoformat(fecha_pago)

    db.session.commit()

    return jsonify({"message": "Reserva confirmada", "reserva": reserva.to_dict_public()})


# ================== COMENTARIOS (MODERACIÓN) =====================
@admin_bp.get("/comentarios")
def admin_list_comentarios():
    # OJO: esta versión ya no exige admin ni token.
    # Úsala solo para devolver lo que quieras mostrar en la web pública.

    estado = request.args.get("estado")
    q = Comentario.query

    if estado:
        estado_normalizado = estado.strip().lower()
        mapping = {
            "pendiente": ComentarioEstado.PENDIENTE,
            "aprobado": ComentarioEstado.APROBADO,
            "rechazado": ComentarioEstado.RECHAZADO,
        }
        estado_enum = mapping.get(estado_normalizado)
        if estado_enum:
            q = q.filter_by(estado=estado_enum)

    comentarios = q.order_by(Comentario.created_at.desc()).all()

    return jsonify([
        {
            "id": c.id,
            "tour_id": c.tour_id,
            "usuario_id": c.usuario_id,
            "calificacion": c.calificacion,
            "comentario": c.comentario,
            "estado": c.estado.value,
            "respuesta_admin": c.respuesta_admin,
            "created_at": c.created_at.isoformat(),
        }
        for c in comentarios
    ])

@admin_bp.patch("/comentarios/<int:comentario_id>/aprobar")
@jwt_required()
def admin_aprobar_comentario(comentario_id):
    _, error = _require_admin()
    if error:
        return error

    comentario = Comentario.query.get(comentario_id)
    if not comentario:
        return jsonify({"message": "Comentario no encontrado"}), 404

    comentario.estado = ComentarioEstado.APROBADO
    db.session.commit()
    return jsonify({"message": "Comentario aprobado"})


@admin_bp.patch("/comentarios/<int:comentario_id>/rechazar")
@jwt_required()
def admin_rechazar_comentario(comentario_id):
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    comentario = Comentario.query.get(comentario_id)
    if not comentario:
        return jsonify({"message": "Comentario no encontrado"}), 404

    comentario.estado = ComentarioEstado.RECHAZADO
    comentario.respuesta_admin = data.get("respuesta_admin")
    db.session.commit()
    return jsonify({"message": "Comentario rechazado"})


@admin_bp.delete("/comentarios/<int:comentario_id>")
@jwt_required()
def admin_eliminar_comentario(comentario_id):
    """
    Elimina permanentemente un comentario.
    Solo admins pueden eliminar comentarios.
    """
    comentario = Comentario.query.get(comentario_id)
    if not comentario:
        return jsonify({"message": "Comentario no encontrado"}), 404

    db.session.delete(comentario)
    db.session.commit()
    return jsonify({"message": "Comentario eliminado permanentemente"})


@admin_bp.route('/guias/<int:id>/foto', methods=['POST'])
def upload_foto_guia(id):
    guia = Guia.query.get_or_404(id)

    # 1. Verificar si enviaron el archivo
    if 'foto' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400
    
    file = request.files['foto']
    
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    if file:
        # 2. Limpiar el nombre del archivo (seguridad)
        filename = secure_filename(file.filename)
        
        # 3. Definir dónde guardar (Ej: carpeta 'static/uploads/guias')
        # Asegúrate de crear esta carpeta en tu proyecto
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'guias')
        os.makedirs(upload_folder, exist_ok=True) # Crea la carpeta si no existe
        
        path_completo = os.path.join(upload_folder, filename)
        file.save(path_completo)
        
        # 4. Actualizar la base de datos con la URL relativa
        # Usamos '/' para que funcione en web
        guia.foto_url = f"/static/uploads/guias/{filename}"
        db.session.commit()

        return jsonify({
            "mensaje": "Foto actualizada correctamente",
            "url": guia.foto_url
        }), 200

# ================== USUARIOS (Para selectores) =====================

@admin_bp.get("/usuarios")
@jwt_required()
def admin_list_usuarios():
    _, error = _require_admin()
    if error:
        return error

    # Traemos solo usuarios activos para no llenar la lista de basura
    usuarios = Usuario.query.filter_by(activo=True).order_by(Usuario.nombre.asc()).all()
    
    return jsonify([
        {
            "id": u.id,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "email": u.email,
            "rol": u.rol
        } 
        for u in usuarios
    ])

@admin_bp.put("/incluye/<int:item_id>")
@jwt_required()
def admin_update_incluye(item_id):
    """Edita un ítem de incluye/no incluye"""
    _, error = _require_admin()
    if error:
        return error

    item = TourIncluye.query.get(item_id)
    if not item:
        return jsonify({"message": "Ítem no encontrado"}), 404

    data = request.get_json() or {}

    # Actualizar tipo si se envía
    if "tipo" in data:
        tipo_raw = str(data.get("tipo", "")).strip().lower()
        if tipo_raw == "incluye":
            item.tipo = IncluyeTipo.INCLUYE
        elif tipo_raw in ("no_incluye", "no incluye", "no-incluye"):
            item.tipo = IncluyeTipo.NO_INCLUYE
        else:
            return jsonify({
                "message": "Tipo inválido. Debe ser 'incluye' o 'no_incluye'"
            }), 400

    # Actualizar descripción si se envía
    if "descripcion" in data:
        item.descripcion = data["descripcion"]

    # Actualizar orden si se envía
    if "orden" in data:
        item.orden = data["orden"]

    db.session.commit()

    return jsonify({"message": "Ítem actualizado", "item": item.to_dict()})


@admin_bp.delete("/incluye/<int:item_id>")
@jwt_required()
def admin_delete_incluye(item_id):
    _, error = _require_admin()
    if error:
        return error

    item = TourIncluye.query.get(item_id)
    if not item:
        return jsonify({"message": "Ítem no encontrado"}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Ítem eliminado correctamente"})

@admin_bp.get("/reservas/<int:reserva_id>")
@jwt_required()
def admin_get_reserva(reserva_id):
    _, error = _require_admin()
    if error: return error

    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404

    # Devolvemos la reserva y también datos extra para facilitar la edición
    return jsonify({
        "reserva": reserva.to_dict_public(),
        # Enviamos IDs crudos para que el frontend pueda pre-seleccionar los selectores
        "raw_ids": {
            "usuario_id": reserva.usuario_id,
            "tour_id": reserva.tour_id,
            "fecha_tour_id": reserva.fecha_tour_id
        }
    })

@admin_bp.put("/reservas/<int:reserva_id>")
@jwt_required()
def admin_update_reserva(reserva_id):
    _, error = _require_admin()
    if error: return error

    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404

    data = request.get_json() or {}
    
    # Actualizar campos permitidos
    if "numero_personas" in data:
        reserva.numero_personas = int(data["numero_personas"])
    
    if "monto_total" in data:
        reserva.monto_total = data["monto_total"]
    
    if "estado_reserva" in data:
        reserva.estado_reserva = data["estado_reserva"]
    
    if "estado_pago" in data:
        reserva.estado_pago = data["estado_pago"]
        
    if "metodo_pago_externo" in data:
        reserva.metodo_pago_externo = data["metodo_pago_externo"]
        
    if "referencia_pago" in data:
        reserva.referencia_pago = data["referencia_pago"]
    
    # ⭐ AGREGAR ESTA LÍNEA:
    if "usuario_id" in data:
        reserva.usuario_id = int(data["usuario_id"])
        
    if "tour_id" in data:
        reserva.tour_id = int(data["tour_id"])
    if "fecha_tour_id" in data:
        reserva.fecha_tour_id = int(data["fecha_tour_id"])

    db.session.commit()
    return jsonify({"message": "Reserva actualizada", "reserva": reserva.to_dict_public()})

# =====================================================
# AGREGAR ESTO A admin_routes.py - GESTIÓN DE USUARIOS/CLIENTES
# =====================================================

# ================== USUARIOS Y CLIENTES (ADMIN) =====================

@admin_bp.get("/usuarios/completo")
@jwt_required()
def admin_list_usuarios_completo():
    """
    Lista todos los usuarios con estadísticas de reservas.
    Soporta filtros: rol, activo, busqueda
    """
    _, error = _require_admin()
    if error:
        return error

    # Filtros
    rol_filter = request.args.get("rol")
    activo_filter = request.args.get("activo")
    busqueda = request.args.get("busqueda", "").strip()

    q = Usuario.query

    # Filtrar por rol
    if rol_filter:
        q = q.filter(Usuario.rol == rol_filter.lower())

    # Filtrar por activo
    if activo_filter is not None:
        if activo_filter.lower() in ("true", "1", "si"):
            q = q.filter(Usuario.activo == True)
        elif activo_filter.lower() in ("false", "0", "no"):
            q = q.filter(Usuario.activo == False)

    # Búsqueda por nombre o email
    if busqueda:
        q = q.filter(
            db.or_(
                Usuario.nombre.ilike(f"%{busqueda}%"),
                Usuario.apellido.ilike(f"%{busqueda}%"),
                Usuario.email.ilike(f"%{busqueda}%")
            )
        )

    usuarios = q.order_by(Usuario.created_at.desc()).all()

    resultado = []
    for u in usuarios:
        # Contar reservas del usuario
        total_reservas = Reserva.query.filter_by(usuario_id=u.id).count()
        reservas_confirmadas = Reserva.query.filter_by(
            usuario_id=u.id, 
            estado_reserva=ReservaEstado.CONFIRMADA
        ).count()
        reservas_canceladas = Reserva.query.filter(
            Reserva.usuario_id == u.id,
            Reserva.estado_reserva.in_([ReservaEstado.CANCELADA_CLIENTE, ReservaEstado.CANCELADA_OPERADOR])
        ).count()
        
        # Calcular monto total gastado
        monto_total_gastado = db.session.query(func.sum(Reserva.monto_total)).filter(
            Reserva.usuario_id == u.id,
            Reserva.estado_pago == PagoEstado.PAGADO
        ).scalar() or 0

        # Última reserva
        ultima_reserva = Reserva.query.filter_by(usuario_id=u.id)\
            .order_by(Reserva.created_at.desc()).first()

        resultado.append({
            "id": u.id,
            "nombre": u.nombre,
            "apellido": getattr(u, 'apellido', None),
            "email": u.email,
            "telefono": getattr(u, 'telefono', None),
            "pais": getattr(u, 'pais', None),
            "rol": u.rol,
            "activo": u.activo,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            
            # ⭐ ESTADÍSTICAS
            "stats": {
                "total_reservas": total_reservas,
                "reservas_confirmadas": reservas_confirmadas,
                "reservas_canceladas": reservas_canceladas,
                "monto_total_gastado": float(monto_total_gastado),
                "ultima_reserva": ultima_reserva.created_at.isoformat() if ultima_reserva else None,
            }
        })

    # Stats generales
    stats_generales = {
        "total_usuarios": Usuario.query.count(),
        "total_clientes": Usuario.query.filter_by(rol="cliente").count(),
        "total_admins": Usuario.query.filter(Usuario.rol.in_(["admin", "super_admin"])).count(),
        "usuarios_activos": Usuario.query.filter_by(activo=True).count(),
        "usuarios_inactivos": Usuario.query.filter_by(activo=False).count(),
    }

    return jsonify({
        "usuarios": resultado,
        "stats": stats_generales
    })


@admin_bp.get("/usuarios/<int:usuario_id>/detalle")
@jwt_required()
def admin_get_usuario_detalle(usuario_id):
    """
    Obtiene el detalle completo de un usuario incluyendo historial de reservas.
    """
    _, error = _require_admin()
    if error:
        return error

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # Obtener todas las reservas del usuario
    reservas = Reserva.query.filter_by(usuario_id=usuario.id)\
        .order_by(Reserva.created_at.desc()).all()

    historial_reservas = []
    for r in reservas:
        tour = Tour.query.get(r.tour_id)
        fecha = FechaTour.query.get(r.fecha_tour_id) if r.fecha_tour_id else None
        
        historial_reservas.append({
            "id": r.id,
            "tour_id": r.tour_id,
            "tour_nombre": tour.nombre if tour else None,
            "fecha_inicio": fecha.fecha_inicio.isoformat() if fecha and fecha.fecha_inicio else None,
            "fecha_fin": fecha.fecha_fin.isoformat() if fecha and fecha.fecha_fin else None,
            "numero_personas": r.numero_personas,
            "monto_total": float(r.monto_total) if r.monto_total else 0,
            "moneda": r.moneda,
            "estado_reserva": r.estado_reserva.value if hasattr(r.estado_reserva, 'value') else r.estado_reserva,
            "estado_pago": r.estado_pago.value if hasattr(r.estado_pago, 'value') else r.estado_pago,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    # Obtener comentarios del usuario
    comentarios = Comentario.query.filter_by(usuario_id=usuario.id)\
        .order_by(Comentario.created_at.desc()).all()

    historial_comentarios = []
    for c in comentarios:
        tour = Tour.query.get(c.tour_id)
        historial_comentarios.append({
            "id": c.id,
            "tour_id": c.tour_id,
            "tour_nombre": tour.nombre if tour else None,
            "calificacion": c.calificacion,
            "comentario": c.comentario,
            "estado": c.estado.value if hasattr(c.estado, 'value') else c.estado,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # Calcular estadísticas
    total_reservas = len(reservas)
    reservas_confirmadas = len([r for r in reservas if r.estado_reserva == ReservaEstado.CONFIRMADA])
    monto_total_gastado = sum([float(r.monto_total or 0) for r in reservas if r.estado_pago == PagoEstado.PAGADO])
    promedio_calificacion = sum([c.calificacion for c in comentarios if c.calificacion]) / len(comentarios) if comentarios else 0

    return jsonify({
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellido": getattr(usuario, 'apellido', None),
            "email": usuario.email,
            "telefono": getattr(usuario, 'telefono', None),
            "pais": getattr(usuario, 'pais', None),
            "rol": usuario.rol,
            "activo": usuario.activo,
            "created_at": usuario.created_at.isoformat() if usuario.created_at else None,
        },
        "stats": {
            "total_reservas": total_reservas,
            "reservas_confirmadas": reservas_confirmadas,
            "monto_total_gastado": monto_total_gastado,
            "total_comentarios": len(comentarios),
            "promedio_calificacion": round(promedio_calificacion, 1),
        },
        "historial_reservas": historial_reservas,
        "historial_comentarios": historial_comentarios,
    })


@admin_bp.put("/usuarios/<int:usuario_id>")
@jwt_required()
def admin_update_usuario(usuario_id):
    """
    Actualiza los datos de un usuario (incluyendo rol).
    """
    admin, error = _require_admin()
    if error:
        return error

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    data = request.get_json() or {}

    # Campos actualizables
    campos_permitidos = ["nombre", "apellido", "telefono", "pais", "activo"]
    
    for campo in campos_permitidos:
        if campo in data:
            setattr(usuario, campo, data[campo])

    # Cambio de rol (solo super_admin puede cambiar roles)
    if "rol" in data:
        nuevo_rol = data["rol"].lower()
        roles_validos = ["cliente", "admin", "super_admin"]
        
        if nuevo_rol not in roles_validos:
            return jsonify({"message": f"Rol inválido. Debe ser: {', '.join(roles_validos)}"}), 400
        
        # Solo super_admin puede crear otros admins
        if nuevo_rol in ["admin", "super_admin"] and admin.rol != "super_admin":
            return jsonify({"message": "Solo un super_admin puede asignar roles de administrador"}), 403
        
        # No permitir degradarse a sí mismo
        if usuario.id == admin.id and nuevo_rol == "cliente":
            return jsonify({"message": "No puedes degradar tu propio rol"}), 400
            
        usuario.rol = nuevo_rol

    db.session.commit()

    return jsonify({
        "message": "Usuario actualizado correctamente",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellido": getattr(usuario, 'apellido', None),
            "email": usuario.email,
            "telefono": getattr(usuario, 'telefono', None),
            "pais": getattr(usuario, 'pais', None),
            "rol": usuario.rol,
            "activo": usuario.activo,
        }
    })


@admin_bp.patch("/usuarios/<int:usuario_id>/toggle-activo")
@jwt_required()
def admin_toggle_usuario_activo(usuario_id):
    """
    Activa o desactiva un usuario.
    """
    admin, error = _require_admin()
    if error:
        return error

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # No permitir desactivarse a sí mismo
    if usuario.id == admin.id:
        return jsonify({"message": "No puedes desactivar tu propia cuenta"}), 400

    usuario.activo = not usuario.activo
    db.session.commit()

    return jsonify({
        "message": f"Usuario {'activado' if usuario.activo else 'desactivado'}",
        "activo": usuario.activo
    })


@admin_bp.patch("/usuarios/<int:usuario_id>/cambiar-rol")
@jwt_required()
def admin_cambiar_rol_usuario(usuario_id):
    """
    Cambia el rol de un usuario.
    """
    admin, error = _require_admin()
    if error:
        return error

    # Solo super_admin puede cambiar roles
    if admin.rol != "super_admin":
        return jsonify({"message": "Solo un super_admin puede cambiar roles"}), 403

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    data = request.get_json() or {}
    nuevo_rol = data.get("rol", "").lower()

    roles_validos = ["cliente", "admin", "super_admin"]
    if nuevo_rol not in roles_validos:
        return jsonify({"message": f"Rol inválido. Opciones: {', '.join(roles_validos)}"}), 400

    # No permitir degradarse a sí mismo
    if usuario.id == admin.id and nuevo_rol == "cliente":
        return jsonify({"message": "No puedes degradar tu propio rol"}), 400

    usuario.rol = nuevo_rol
    db.session.commit()

    return jsonify({
        "message": f"Rol cambiado a '{nuevo_rol}'",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
        }
    })


@admin_bp.post("/usuarios/crear")
@jwt_required()
def admin_crear_usuario():
    """
    Crea un nuevo usuario desde el panel de admin.
    """
    admin, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}

    # Campos requeridos
    required = ["nombre", "email", "password"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios: nombre, email, password"}), 400

    # Verificar email único
    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"message": "El email ya está registrado"}), 400

    # Determinar rol
    rol = data.get("rol", "cliente").lower()
    roles_validos = ["cliente", "admin", "super_admin"]
    
    if rol not in roles_validos:
        return jsonify({"message": f"Rol inválido. Opciones: {', '.join(roles_validos)}"}), 400

    # Solo super_admin puede crear admins
    if rol in ["admin", "super_admin"] and admin.rol != "super_admin":
        return jsonify({"message": "Solo un super_admin puede crear administradores"}), 403

    usuario = Usuario(
        nombre=data["nombre"],
        apellido=data.get("apellido"),
        email=data["email"],
        telefono=data.get("telefono"),
        pais=data.get("pais"),
        rol=rol,
        activo=data.get("activo", True),
    )
    usuario.set_password(data["password"])

    db.session.add(usuario)
    db.session.commit()

    return jsonify({
        "message": "Usuario creado correctamente",
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
        }
    }), 201


@admin_bp.delete("/usuarios/<int:usuario_id>")
@jwt_required()
def admin_delete_usuario(usuario_id):
    """
    Elimina un usuario (soft delete - lo desactiva).
    """
    admin, error = _require_admin()
    if error:
        return error

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # No permitir eliminarse a sí mismo
    if usuario.id == admin.id:
        return jsonify({"message": "No puedes eliminar tu propia cuenta"}), 400

    # No permitir eliminar super_admins si no eres super_admin
    if usuario.rol == "super_admin" and admin.rol != "super_admin":
        return jsonify({"message": "Solo un super_admin puede eliminar otros super_admins"}), 403

    # Soft delete
    usuario.activo = False
    db.session.commit()

    return jsonify({"message": "Usuario eliminado (desactivado)"})


# ================== BANNERS DE TOUR =====================

@admin_bp.get("/tours/<int:tour_id>/banners")
@jwt_required()
def admin_list_banners(tour_id):
    """Lista todos los banners de un tour."""
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    banners = TourBanner.query.filter_by(tour_id=tour_id)\
        .order_by(TourBanner.orden.asc()).all()

    return jsonify([b.to_dict() for b in banners])
# =====================================================
# REEMPLAZA EN admin_routes.py - Función admin_create_banner
# =====================================================

@admin_bp.post("/tours/<int:tour_id>/banners")
@jwt_required()
def admin_create_banner(tour_id):
    """
    Crea un banner para un tour.
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    media_url = None
    poster_url = None
    tipo_str = "imagen"

    try:
        # Procesar archivos si es multipart
        if "file" in request.files:
            file = request.files["file"]
            
            if file.filename == "":
                return jsonify({"message": "Nombre de archivo vacío"}), 400

            # Determinar si es imagen o video por extensión
            ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
            allowed_images = {"png", "jpg", "jpeg", "webp", "gif"}
            allowed_videos = {"mp4", "webm", "mov", "avi"}

            if ext not in allowed_images and ext not in allowed_videos:
                return jsonify({"message": f"Tipo de archivo no permitido: .{ext}"}), 400

            # Determinar tipo
            tipo_str = "video" if ext in allowed_videos else "imagen"
            
            filename = secure_filename(file.filename)
            
            # Carpeta: uploads/tours/<tour_id>/banners/
            folder = os.path.join("tours", str(tour.id), "banners")
            upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
            os.makedirs(upload_folder, exist_ok=True)

            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            # Construir URL
            media_url = f"/uploads/tours/{tour.id}/banners/{filename}"
            
            # Procesar poster si viene
            if "poster" in request.files:
                poster_file = request.files["poster"]
                if poster_file.filename:
                    poster_filename = secure_filename(poster_file.filename)
                    poster_path = os.path.join(upload_folder, f"poster_{poster_filename}")
                    poster_file.save(poster_path)
                    poster_url = f"/uploads/tours/{tour.id}/banners/poster_{poster_filename}"

            data = request.form
        else:
            data = request.get_json() or {}
            media_url = data.get("media_url")
            poster_url = data.get("poster_url")
            tipo_str = data.get("tipo", "imagen").lower()

        if not media_url:
            return jsonify({"message": "Debe proporcionar un archivo o media_url"}), 400

        # ⭐ USAR EL ENUM CORRECTAMENTE (minúsculas)
        tipo_enum = MediaTipo.video if tipo_str == "video" else MediaTipo.imagen

        # Si es_principal, quitar principal de otros banners
        es_principal = data.get("es_principal", "false")
        if isinstance(es_principal, str):
            es_principal = es_principal.lower() in ("true", "1", "yes", "si")
        
        if es_principal:
            TourBanner.query.filter_by(tour_id=tour.id, es_principal=True)\
                .update({"es_principal": False})

        # Crear banner
        banner = TourBanner(
            tour_id=tour.id,
            tipo=tipo_enum,  # ⭐ USAR ENUM
            media_url=media_url,
            poster_url=poster_url,
            titulo=data.get("titulo"),
            subtitulo=data.get("subtitulo"),
            texto_boton=data.get("texto_boton"),
            orden=int(data.get("orden", 0)),
            activo=True,
            es_principal=es_principal,
            overlay_opacity=float(data.get("overlay_opacity", 0.35)),
            posicion_vertical=data.get("posicion_vertical", "center"),
        )

        db.session.add(banner)
        db.session.commit()

        return jsonify({
            "message": "Banner creado exitosamente",
            "banner": banner.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Error al crear banner: {str(e)}"}), 500
    
@admin_bp.put("/banners/<int:banner_id>")
@jwt_required()
def admin_update_banner(banner_id):
    """Actualiza un banner existente."""
    _, error = _require_admin()
    if error:
        return error

    banner = TourBanner.query.get(banner_id)
    if not banner:
        return jsonify({"message": "Banner no encontrado"}), 404

    data = request.get_json() or {}

    # Actualizar campos
    if "titulo" in data:
        banner.titulo = data["titulo"]
    if "subtitulo" in data:
        banner.subtitulo = data["subtitulo"]
    if "texto_boton" in data:
        banner.texto_boton = data["texto_boton"]
    if "orden" in data:
        banner.orden = int(data["orden"])
    if "activo" in data:
        banner.activo = data["activo"]
    if "overlay_opacity" in data:
        banner.overlay_opacity = float(data["overlay_opacity"])
    if "posicion_vertical" in data:
        banner.posicion_vertical = data["posicion_vertical"]
    
    # Si se marca como principal, quitar de otros
    if data.get("es_principal"):
        TourBanner.query.filter(
            TourBanner.tour_id == banner.tour_id,
            TourBanner.id != banner.id,
            TourBanner.es_principal == True
        ).update({"es_principal": False})
        banner.es_principal = True
    elif "es_principal" in data:
        banner.es_principal = data["es_principal"]

    db.session.commit()

    return jsonify({
        "message": "Banner actualizado",
        "banner": banner.to_dict()
    })


@admin_bp.delete("/banners/<int:banner_id>")
@jwt_required()
def admin_delete_banner(banner_id):
    """Elimina un banner."""
    _, error = _require_admin()
    if error:
        return error

    banner = TourBanner.query.get(banner_id)
    if not banner:
        return jsonify({"message": "Banner no encontrado"}), 404

    # Opcionalmente eliminar archivo físico
    # if banner.media_url and banner.media_url.startswith("/uploads/"):
    #     filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], banner.media_url.replace("/uploads/", ""))
    #     if os.path.exists(filepath):
    #         os.remove(filepath)

    db.session.delete(banner)
    db.session.commit()

    return jsonify({"message": "Banner eliminado"})


@admin_bp.patch("/banners/<int:banner_id>/toggle")
@jwt_required()
def admin_toggle_banner(banner_id):
    """Activa/desactiva un banner."""
    _, error = _require_admin()
    if error:
        return error

    banner = TourBanner.query.get(banner_id)
    if not banner:
        return jsonify({"message": "Banner no encontrado"}), 404

    banner.activo = not banner.activo
    db.session.commit()

    return jsonify({
        "message": f"Banner {'activado' if banner.activo else 'desactivado'}",
        "activo": banner.activo
    })


@admin_bp.patch("/banners/<int:banner_id>/set-principal")
@jwt_required()
def admin_set_banner_principal(banner_id):
    """Establece un banner como principal."""
    _, error = _require_admin()
    if error:
        return error

    banner = TourBanner.query.get(banner_id)
    if not banner:
        return jsonify({"message": "Banner no encontrado"}), 404

    # Quitar principal de otros
    TourBanner.query.filter(
        TourBanner.tour_id == banner.tour_id,
        TourBanner.id != banner.id
    ).update({"es_principal": False})

    banner.es_principal = True
    db.session.commit()

    return jsonify({
        "message": "Banner establecido como principal",
        "banner": banner.to_dict()
    })


@admin_bp.post("/banners/reorder")
@jwt_required()
def admin_reorder_banners():
    """
    Reordena los banners de un tour.
    Body: { "orden": [id1, id2, id3, ...] }
    """
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    orden_ids = data.get("orden", [])

    if not orden_ids:
        return jsonify({"message": "Debe proporcionar lista de IDs"}), 400

    for idx, banner_id in enumerate(orden_ids):
        TourBanner.query.filter_by(id=banner_id).update({"orden": idx})

    db.session.commit()

    return jsonify({"message": "Orden actualizado"})


# ================== UBICACIONES DEL TOUR (PARA MAPAS) =====================

@admin_bp.get("/tours/<int:tour_id>/ubicaciones")
@jwt_required()
def admin_list_ubicaciones(tour_id):
    """Lista todas las ubicaciones de un tour."""
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    ubicaciones = TourUbicacion.query.filter_by(tour_id=tour_id)\
        .order_by(TourUbicacion.orden.asc()).all()

    return jsonify([u.to_dict() for u in ubicaciones])


@admin_bp.post("/tours/<int:tour_id>/ubicaciones")
@jwt_required()
def admin_create_ubicacion(tour_id):
    """
    Crea una ubicacion para un tour.
    Body JSON:
    {
        "nombre": "Quito",
        "pais": "Ecuador",
        "provincia": "Pichincha",
        "ciudad": "Quito",
        "descripcion": "Capital de Ecuador...",
        "latitud": -0.180653,
        "longitud": -78.467838,
        "orden": 1,
        "dia_inicio": 1,
        "dia_fin": 1,
        "tipo_ubicacion": "origen",
        "imagen_url": "/uploads/..."
    }
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}

    # Campos requeridos
    if not data.get("nombre"):
        return jsonify({"message": "El campo 'nombre' es obligatorio"}), 400

    # Usar el pais del tour si no se especifica
    pais = data.get("pais") or tour.pais

    ubicacion = TourUbicacion(
        tour_id=tour.id,
        nombre=data["nombre"],
        pais=pais,
        provincia=data.get("provincia"),
        ciudad=data.get("ciudad"),
        descripcion=data.get("descripcion"),
        latitud=data.get("latitud"),
        longitud=data.get("longitud"),
        orden=data.get("orden", 1),
        dia_inicio=data.get("dia_inicio"),
        dia_fin=data.get("dia_fin"),
        tipo_ubicacion=data.get("tipo_ubicacion", "destino"),
        imagen_url=data.get("imagen_url"),
        activo=data.get("activo", True),
    )

    db.session.add(ubicacion)
    db.session.commit()

    return jsonify({
        "message": "Ubicacion creada exitosamente",
        "ubicacion": ubicacion.to_dict()
    }), 201


@admin_bp.put("/ubicaciones/<int:ubicacion_id>")
@jwt_required()
def admin_update_ubicacion(ubicacion_id):
    """Actualiza una ubicacion existente."""
    _, error = _require_admin()
    if error:
        return error

    ubicacion = TourUbicacion.query.get(ubicacion_id)
    if not ubicacion:
        return jsonify({"message": "Ubicacion no encontrada"}), 404

    data = request.get_json() or {}

    # Campos actualizables
    campos = [
        "nombre", "pais", "provincia", "ciudad", "descripcion",
        "latitud", "longitud", "orden", "dia_inicio", "dia_fin",
        "tipo_ubicacion", "imagen_url", "activo"
    ]

    for campo in campos:
        if campo in data:
            setattr(ubicacion, campo, data[campo])

    db.session.commit()

    return jsonify({
        "message": "Ubicacion actualizada",
        "ubicacion": ubicacion.to_dict()
    })


@admin_bp.delete("/ubicaciones/<int:ubicacion_id>")
@jwt_required()
def admin_delete_ubicacion(ubicacion_id):
    """Elimina una ubicacion."""
    _, error = _require_admin()
    if error:
        return error

    ubicacion = TourUbicacion.query.get(ubicacion_id)
    if not ubicacion:
        return jsonify({"message": "Ubicacion no encontrada"}), 404

    db.session.delete(ubicacion)
    db.session.commit()

    return jsonify({"message": "Ubicacion eliminada"})


@admin_bp.post("/tours/<int:tour_id>/ubicaciones/batch")
@jwt_required()
def admin_create_ubicaciones_batch(tour_id):
    """
    Crea multiples ubicaciones de una vez.
    Body JSON:
    {
        "ubicaciones": [
            {"nombre": "Quito", "latitud": -0.18, "longitud": -78.46, "orden": 1},
            {"nombre": "Cuenca", "latitud": -2.90, "longitud": -79.00, "orden": 2}
        ]
    }
    """
    _, error = _require_admin()
    if error:
        return error

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}
    ubicaciones_data = data.get("ubicaciones", [])

    if not ubicaciones_data:
        return jsonify({"message": "Debe proporcionar al menos una ubicacion"}), 400

    creadas = []
    for ub_data in ubicaciones_data:
        if not ub_data.get("nombre"):
            continue

        ubicacion = TourUbicacion(
            tour_id=tour.id,
            nombre=ub_data["nombre"],
            pais=ub_data.get("pais") or tour.pais,
            provincia=ub_data.get("provincia"),
            ciudad=ub_data.get("ciudad"),
            descripcion=ub_data.get("descripcion"),
            latitud=ub_data.get("latitud"),
            longitud=ub_data.get("longitud"),
            orden=ub_data.get("orden", 1),
            dia_inicio=ub_data.get("dia_inicio"),
            dia_fin=ub_data.get("dia_fin"),
            tipo_ubicacion=ub_data.get("tipo_ubicacion", "destino"),
            imagen_url=ub_data.get("imagen_url"),
            activo=True,
        )
        db.session.add(ubicacion)
        creadas.append(ubicacion)

    db.session.commit()

    return jsonify({
        "message": f"{len(creadas)} ubicaciones creadas",
        "ubicaciones": [u.to_dict() for u in creadas]
    }), 201


@admin_bp.post("/ubicaciones/reorder")
@jwt_required()
def admin_reorder_ubicaciones():
    """
    Reordena las ubicaciones de un tour.
    Body: { "orden": [id1, id2, id3, ...] }
    """
    _, error = _require_admin()
    if error:
        return error

    data = request.get_json() or {}
    orden_ids = data.get("orden", [])

    if not orden_ids:
        return jsonify({"message": "Debe proporcionar lista de IDs"}), 400

    for idx, ubicacion_id in enumerate(orden_ids):
        TourUbicacion.query.filter_by(id=ubicacion_id).update({"orden": idx + 1})

    db.session.commit()

    return jsonify({"message": "Orden actualizado"})


# ================== GALERIA - Actualizar descripcion =====================

@admin_bp.put("/galeria/<int:item_id>")
@jwt_required()
def admin_update_galeria(item_id):
    """Actualiza una imagen de galeria (descripcion, orden, categoria)."""
    _, error = _require_admin()
    if error:
        return error

    item = Galeria.query.get(item_id)
    if not item:
        return jsonify({"message": "Elemento de galeria no encontrado"}), 404

    data = request.get_json() or {}

    if "descripcion" in data:
        item.descripcion = data["descripcion"]
    if "orden" in data:
        item.orden = data["orden"]
    if "categoria" in data:
        item.categoria = data["categoria"]

    db.session.commit()

    return jsonify({
        "message": "Galeria actualizada",
        "galeria": item.to_dict()
    })


# ================== ELIMINACIÓN PERMANENTE =====================

@admin_bp.delete("/reservas/<int:reserva_id>/permanente")
@jwt_required()
def admin_delete_reserva_permanente(reserva_id):
    """
    Elimina una reserva PERMANENTEMENTE de la base de datos.
    CUIDADO: Esta acción no se puede deshacer.
    """
    _, error = _require_admin()
    if error:
        return error

    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404

    try:
        info = {
            "id": reserva.id,
            "tour": reserva.tour.nombre if reserva.tour else "N/A",
            "usuario": reserva.usuario.email if reserva.usuario else "N/A"
        }

        db.session.delete(reserva)
        db.session.commit()

        return jsonify({
            "message": f"Reserva #{info['id']} eliminada permanentemente",
            "deleted": info
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": f"Error al eliminar reserva: {str(e)}"
        }), 500


@admin_bp.delete("/usuarios/<int:usuario_id>/permanente")
@jwt_required()
def admin_delete_usuario_permanente(usuario_id):
    """
    Elimina un usuario PERMANENTEMENTE de la base de datos.
    CUIDADO: Esta acción no se puede deshacer.
    Elimina: reservas, comentarios y consultas del usuario.
    """
    admin, error = _require_admin()
    if error:
        return error

    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # No permitir eliminarse a sí mismo
    if usuario.id == admin.id:
        return jsonify({"message": "No puedes eliminar tu propia cuenta"}), 400

    # Solo super_admin puede eliminar otros super_admins
    if usuario.rol == "super_admin" and admin.rol != "super_admin":
        return jsonify({"message": "Solo un super_admin puede eliminar otros super_admins"}), 403

    try:
        nombre_usuario = f"{usuario.nombre} ({usuario.email})"

        # 1. Eliminar reservas del usuario
        Reserva.query.filter_by(usuario_id=usuario_id).delete()

        # 2. Eliminar comentarios del usuario
        Comentario.query.filter_by(usuario_id=usuario_id).delete()

        # 3. Eliminar consultas del usuario
        ConsultaTour.query.filter_by(usuario_id=usuario_id).delete()

        # 4. Eliminar el usuario
        db.session.delete(usuario)
        db.session.commit()

        return jsonify({
            "message": f"Usuario '{nombre_usuario}' eliminado permanentemente",
            "deleted_id": usuario_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": f"Error al eliminar usuario: {str(e)}"
        }), 500

