# routes/tour_routes.py
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from email_service import enviar_email, ADMIN_EMAIL
from models import (
    Tour,
    Comentario,
    ConsultaTour,
    Usuario,
    ComentarioEstado,
    Reserva,
    FechaTour,
    ReservaEstado,
    PagoEstado,
    Guia,
    TourUbicacion,
    Categoria,
    PortadaHome
)

tour_bp = Blueprint("tours", __name__, url_prefix="/tours")


# ================== PORTADAS (PÚBLICO) =====================

@tour_bp.get("/portadas")
def list_portadas():
    """
    Lista portadas activas. Filtrar por sección: ?seccion=home
    Secciones válidas: home, sobre_nosotros, contactanos
    """
    seccion = request.args.get("seccion")
    query = PortadaHome.query.filter_by(activo=True)
    if seccion:
        query = query.filter_by(seccion=seccion)
    portadas = query.order_by(PortadaHome.orden.asc()).all()
    return jsonify([p.to_dict() for p in portadas])


# ================== CATEGORÍAS (PÚBLICO) =====================

@tour_bp.get("/categorias")
def list_categorias():
    """
    Lista todas las categorías activas con sus tours.
    Ideal para el menú de navegación/header.
    """
    categorias = Categoria.query.filter_by(activo=True).order_by(Categoria.orden).all()
    return jsonify([c.to_dict_with_tours() for c in categorias])


@tour_bp.get("/categorias/<slug>")
def get_categoria(slug):
    """
    Detalle de una categoría con todos sus tours activos.
    """
    categoria = Categoria.query.filter_by(slug=slug, activo=True).first()
    if not categoria:
        return jsonify({"message": "Categoría no encontrada"}), 404

    return jsonify(categoria.to_dict_with_tours())


# ================== TOURS (PÚBLICO) =====================

@tour_bp.get("")
def list_tours():
    """
    Listado de tours para la página de catálogo.
    Filtros opcionales: ?pais=ecuador&categoria=galapagos
    """
    pais = request.args.get("pais")
    categoria_slug = request.args.get("categoria")

    q = Tour.query.filter_by(activo=True)

    if pais:
        q = q.filter(Tour.pais.ilike(f"%{pais}%"))

    if categoria_slug:
        categoria = Categoria.query.filter_by(slug=categoria_slug).first()
        if categoria:
            q = q.filter(Tour.categoria_id == categoria.id)

    tours = q.order_by(Tour.orden_destacado.nullslast()).all()
    return jsonify([t.to_card_dict() for t in tours])


@tour_bp.get("/<slug>")
def get_tour(slug):
    """
    Detalle de un tour + comentarios aprobados.
    URL: /tours/<slug>
    """
    tour = Tour.query.filter_by(slug=slug, activo=True).first()
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    comentarios = (
        Comentario.query
        .filter(
            Comentario.tour_id == tour.id,
            Comentario.estado == ComentarioEstado.APROBADO,
        )
        .order_by(Comentario.created_at.desc())
        .all()
    )

    return jsonify(
        {
            "tour": tour.to_detail_dict(),
            "comentarios": [c.to_public_dict() for c in comentarios],
        }
    )



# ================== COMENTARIOS (CLIENTE) =====================

@tour_bp.post("/<int:tour_id>/comentarios")
@jwt_required()
def crear_comentario(tour_id):
    """
    Crea un comentario de un usuario sobre un tour.
    El comentario queda en estado 'pendiente' hasta que un admin lo apruebe.
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    tour = Tour.query.get(tour_id)
    if not tour or not tour.activo:
        return jsonify({"message": "Tour no encontrado o inactivo"}), 404

    data = request.get_json() or {}

    required = ["comentario", "calificacion"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    try:
        calificacion = int(data["calificacion"])
    except (ValueError, TypeError):
        return jsonify({"message": "La calificación debe ser un número entero"}), 400

    if calificacion < 1 or calificacion > 5:
        return jsonify({"message": "La calificación debe estar entre 1 y 5"}), 400

    nuevo_comentario = Comentario(
        usuario_id=usuario.id,
        tour_id=tour.id,
        comentario=data["comentario"],
        calificacion=calificacion,
        estado=ComentarioEstado.PENDIENTE,
    )

    db.session.add(nuevo_comentario)
    db.session.commit()

    return jsonify({
        "message": "Comentario enviado y pendiente de aprobación",
        "comentario": nuevo_comentario.to_public_dict(),
    }), 201


# ================== RESERVAS (CLIENTE) - CON ENVÍO DE CORREO =====================

@tour_bp.post("/<int:tour_id>/reservas")
@jwt_required()
def crear_reserva_pre_reserva(tour_id):
    """
    Crea una PRE-RESERVA para un tour.
    Envía correo de confirmación al cliente y notificación al admin.
    URL: POST /tours/<tour_id>/reservas
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    tour = Tour.query.get(tour_id)
    if not tour or not tour.activo:
        return jsonify({"message": "Tour no encontrado o inactivo"}), 404

    data = request.get_json() or {}
    required = ["fecha_tour_id", "numero_personas"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    try:
        fecha_tour_id = int(data["fecha_tour_id"])
        numero_personas = int(data["numero_personas"])
    except (ValueError, TypeError):
        return jsonify({"message": "fecha_tour_id y numero_personas deben ser enteros"}), 400

    if numero_personas < 1:
        return jsonify({"message": "numero_personas debe ser al menos 1"}), 400

    fecha = FechaTour.query.filter_by(id=fecha_tour_id, tour_id=tour.id).first()
    if not fecha:
        return jsonify({"message": "La fecha seleccionada no pertenece a este tour"}), 400

    cupos_disponibles = fecha.cupos_totales - (fecha.cupos_ocupados or 0)
    if numero_personas > cupos_disponibles:
        return jsonify({"message": f"No hay cupos suficientes. Disponibles: {cupos_disponibles}"}), 400

    # Calcular monto
    precio_pp = float(tour.precio_pp) if tour.precio_pp else 0
    monto_total = data.get("monto_total") or (precio_pp * numero_personas)

    # Obtener datos de contacto (del formulario mejorado)
    datos_contacto = data.get("datos_contacto", {})
    email_destino = datos_contacto.get("email") or usuario.email
    nombre_contacto = datos_contacto.get("nombre") or usuario.nombre
    telefono_contacto = datos_contacto.get("telefono") or getattr(usuario, 'telefono', None)

    # Crear reserva
    reserva = Reserva(
        usuario_id=usuario.id,
        tour_id=tour.id,
        fecha_tour_id=fecha.id,
        numero_personas=numero_personas,
        estado_reserva=ReservaEstado.PRE_RESERVA,
        estado_pago=PagoEstado.PENDIENTE,
        monto_total=monto_total,
        moneda=tour.moneda or "USD",
        comentarios_cliente=data.get("comentarios_cliente"),
    )

    fecha.cupos_ocupados = (fecha.cupos_ocupados or 0) + numero_personas

    db.session.add(reserva)
    db.session.commit()

    # ==================== ENVIAR CORREOS ====================
    correo_enviado = False
    try:
        enviar_correo_cliente(reserva, usuario, tour, fecha, email_destino, nombre_contacto)
        enviar_correo_admin(reserva, usuario, tour, fecha, telefono_contacto)
        correo_enviado = True
        print(f"✅ Correos enviados para reserva #{reserva.id}")
    except Exception as e:
        current_app.logger.error(f"❌ Error enviando correo: {str(e)}")
        print(f"❌ Error enviando correo: {str(e)}")

    return jsonify({
        "message": "Pre-reserva creada exitosamente." + (" Te hemos enviado un correo de confirmación." if correo_enviado else " (No se pudo enviar el correo)"),
        "reserva": {
            "id": reserva.id,
            "tour_nombre": tour.nombre,
            "fecha_inicio": fecha.fecha_inicio.isoformat() if fecha.fecha_inicio else None,
            "fecha_fin": fecha.fecha_fin.isoformat() if fecha.fecha_fin else None,
            "numero_personas": reserva.numero_personas,
            "monto_total": float(reserva.monto_total) if reserva.monto_total else 0,
            "moneda": reserva.moneda,
            "estado_reserva": reserva.estado_reserva.value,
            "estado_pago": reserva.estado_pago.value,
        }
    }), 201


@tour_bp.get("/mis-reservas")
@jwt_required()
def listar_mis_reservas():
    """
    Lista todas las reservas del usuario logueado.
    URL: GET /tours/mis-reservas
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    reservas = (
        Reserva.query
        .filter_by(usuario_id=usuario.id)
        .order_by(Reserva.created_at.desc())
        .all()
    )

    return jsonify([r.to_dict_public() for r in reservas])


@tour_bp.get("/mi-perfil/estadisticas")
@jwt_required()
def mis_estadisticas():
    """
    Devuelve estadísticas del usuario logueado:
    - Total de reservas y desglose por estado
    - Total de comentarios y desglose por estado
    - Tours visitados/reservados
    - Gasto total
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # Reservas del usuario
    reservas = Reserva.query.filter_by(usuario_id=usuario.id).all()

    # Conteo por estado de reserva
    reservas_por_estado = {
        "pre_reserva": 0,
        "confirmada": 0,
        "cancelada_cliente": 0,
        "cancelada_operador": 0
    }

    gasto_total = 0
    tours_ids = set()

    for r in reservas:
        estado = r.estado_reserva.value if hasattr(r.estado_reserva, 'value') else str(r.estado_reserva)
        if estado in reservas_por_estado:
            reservas_por_estado[estado] += 1
        tours_ids.add(r.tour_id)
        if r.monto_total and estado == "confirmada":
            gasto_total += float(r.monto_total)

    # Comentarios del usuario
    comentarios = Comentario.query.filter_by(usuario_id=usuario.id).all()

    comentarios_por_estado = {
        "pendiente": 0,
        "aprobado": 0,
        "rechazado": 0
    }

    calificaciones = []
    for c in comentarios:
        estado = c.estado.value if hasattr(c.estado, 'value') else str(c.estado)
        if estado in comentarios_por_estado:
            comentarios_por_estado[estado] += 1
        if c.calificacion:
            calificaciones.append(c.calificacion)

    promedio_calificacion = sum(calificaciones) / len(calificaciones) if calificaciones else 0

    return jsonify({
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "miembro_desde": usuario.created_at.isoformat() if usuario.created_at else None
        },
        "reservas": {
            "total": len(reservas),
            "por_estado": reservas_por_estado,
            "tours_diferentes": len(tours_ids),
            "gasto_total": round(gasto_total, 2)
        },
        "comentarios": {
            "total": len(comentarios),
            "por_estado": comentarios_por_estado,
            "promedio_calificacion": round(promedio_calificacion, 1)
        }
    })


# =====================================================
# FUNCIONES DE ENVÍO DE CORREO
# =====================================================

def enviar_correo_cliente(reserva, usuario, tour, fecha, email_destino, nombre_contacto):
    """Envía correo de confirmación de pre-reserva al cliente"""
    
    fecha_inicio_str = fecha.fecha_inicio.strftime('%d de %B, %Y') if fecha.fecha_inicio else 'Por confirmar'
    fecha_fin_str = fecha.fecha_fin.strftime('%d de %B, %Y') if fecha.fecha_fin else 'Por confirmar'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #fff; }}
            .header {{ background: linear-gradient(135deg, #C1A919 0%, #a08915 100%); color: white; padding: 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .success-icon {{ font-size: 50px; margin-bottom: 10px; }}
            .content {{ padding: 30px; }}
            .info-box {{ background: #fffaf0; border: 1px solid #f0e6c8; border-radius: 10px; padding: 20px; margin: 20px 0; }}
            .info-row {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
            .info-row:last-child {{ border-bottom: none; }}
            .info-label {{ color: #666; font-size: 14px; }}
            .info-value {{ font-weight: bold; color: #333; font-size: 16px; }}
            .total {{ font-size: 28px; color: #C1A919; font-weight: bold; }}
            .cta-button {{ display: inline-block; background: #25D366; color: white; padding: 15px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; margin: 10px 5px; }}
            .footer {{ background: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #888; }}
            .next-steps {{ background: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px 20px; margin: 20px 0; border-radius: 0 10px 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="success-icon">✈️</div>
                <h1>¡Solicitud de Reserva Recibida!</h1>
                <p style="margin: 10px 0 0; opacity: 0.9;">Reserva #{reserva.id}</p>
            </div>
            
            <div class="content">
                <p>Hola <strong>{nombre_contacto}</strong>,</p>
                
                <p>¡Gracias por elegirnos! Hemos recibido tu solicitud de reserva para <strong>{tour.nombre}</strong>.</p>
                
                <p>Nuestro equipo revisará tu solicitud y te contactará en las próximas <strong>24 horas</strong> para confirmar los detalles y coordinar el pago.</p>
                
                <div class="info-box">
                    <h3 style="margin-top: 0; color: #C1A919; border-bottom: 2px solid #f0e6c8; padding-bottom: 10px;">📋 Resumen de tu solicitud</h3>
                    
                    <div class="info-row">
                        <div class="info-label">Número de reserva</div>
                        <div class="info-value">#{reserva.id}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Tour</div>
                        <div class="info-value">{tour.nombre}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Destino</div>
                        <div class="info-value">{tour.pais or 'Ecuador'}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Fecha de salida</div>
                        <div class="info-value">📅 {fecha_inicio_str}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Fecha de regreso</div>
                        <div class="info-value">📅 {fecha_fin_str}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Duración</div>
                        <div class="info-value">{tour.duracion_dias or 'N/A'} días</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Pasajeros</div>
                        <div class="info-value">👥 {reserva.numero_personas} persona(s)</div>
                    </div>
                    <div class="info-row" style="background: #fffaf0; margin: 10px -20px -20px; padding: 20px; border-radius: 0 0 10px 10px;">
                        <div class="info-label">Total estimado</div>
                        <div class="total">${reserva.monto_total} {reserva.moneda}</div>
                    </div>
                </div>
                
                {"<div style='background: #f5f5f5; padding: 15px; border-radius: 10px; margin: 20px 0;'><strong>💬 Tus comentarios:</strong><p style='margin: 10px 0 0; color: #666;'>" + str(reserva.comentarios_cliente) + "</p></div>" if reserva.comentarios_cliente else ""}
                
                <div class="next-steps">
                    <h4 style="margin-top: 0; color: #2e7d32;">📌 ¿Qué sigue?</h4>
                    <p style="margin: 5px 0;">1️⃣ Revisaremos tu solicitud (máximo 24 horas)</p>
                    <p style="margin: 5px 0;">2️⃣ Te contactaremos para confirmar disponibilidad</p>
                    <p style="margin: 5px 0;">3️⃣ Coordinaremos la forma de pago</p>
                    <p style="margin: 5px 0;">4️⃣ ¡Recibirás tu confirmación final!</p>
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="https://wa.me/593985676029?text=Hola! Acabo de hacer una pre-reserva para {tour.nombre}. Mi número es %23{reserva.id}" class="cta-button">
                        📱 Contactar por WhatsApp
                    </a>
                </p>
                
                <p style="text-align: center; color: #888; font-size: 14px; margin-top: 20px;">
                    ¿Tienes preguntas? Responde a este correo o contáctanos por WhatsApp.
                </p>
            </div>
            
            <div class="footer">
                <p style="font-size: 16px; margin-bottom: 5px;"><strong>Mirlo Tours</strong></p>
                <p>🌍 Especialistas en turismo de naturaleza</p>
                <p>📍 Ecuador | 📞 +593 98 567 6029</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
                <p style="font-size: 11px; color: #aaa;">
                    Este correo fue enviado porque solicitaste una reserva en nuestro sitio web.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    enviar_email(
        [email_destino],
        f"✈️ Solicitud de Reserva #{reserva.id} - {tour.nombre}",
        html_content
    )


def enviar_correo_admin(reserva, usuario, tour, fecha, telefono_contacto):
    """Envía notificación al admin sobre nueva pre-reserva"""

    admin_email = ADMIN_EMAIL
    
    fecha_inicio_str = fecha.fecha_inicio.strftime('%d/%m/%Y') if fecha.fecha_inicio else 'Por confirmar'
    fecha_fin_str = fecha.fecha_fin.strftime('%d/%m/%Y') if fecha.fecha_fin else 'Por confirmar'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #fff; }}
            .header {{ background: #C1A919; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 25px; }}
            .alert {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 8px; }}
            .section {{ margin-bottom: 25px; }}
            .section-title {{ font-size: 14px; color: #666; text-transform: uppercase; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .info-table {{ width: 100%; border-collapse: collapse; }}
            .info-table td {{ padding: 10px; border-bottom: 1px solid #f0f0f0; }}
            .info-table td:first-child {{ font-weight: bold; width: 40%; color: #666; }}
            .highlight {{ background: #fffaf0; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; }}
            .highlight .amount {{ font-size: 28px; color: #C1A919; font-weight: bold; }}
            .btn {{ display: inline-block; background: #C1A919; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; }}
            .footer {{ background: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #888; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0;">🔔 Nueva Pre-Reserva #{reserva.id}</h2>
            </div>
            
            <div class="content">
                <div class="alert">
                    <strong>⚠️ Acción requerida:</strong> Un cliente ha solicitado una reserva.
                </div>
                
                <div class="section">
                    <div class="section-title">👤 Datos del Cliente</div>
                    <table class="info-table">
                        <tr>
                            <td>Nombre:</td>
                            <td>{usuario.nombre} {getattr(usuario, 'apellido', '') or ''}</td>
                        </tr>
                        <tr>
                            <td>Email:</td>
                            <td><a href="mailto:{usuario.email}">{usuario.email}</a></td>
                        </tr>
                        <tr>
                            <td>Teléfono:</td>
                            <td>{telefono_contacto or 'No proporcionado'}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="section">
                    <div class="section-title">🏔️ Datos de la Reserva</div>
                    <table class="info-table">
                        <tr>
                            <td>Tour:</td>
                            <td><strong>{tour.nombre}</strong></td>
                        </tr>
                        <tr>
                            <td>Fecha:</td>
                            <td>{fecha_inicio_str} → {fecha_fin_str}</td>
                        </tr>
                        <tr>
                            <td>Pasajeros:</td>
                            <td>{reserva.numero_personas} persona(s)</td>
                        </tr>
                        <tr>
                            <td>Estado:</td>
                            <td><span style="background: #fff3cd; padding: 3px 10px; border-radius: 15px; font-size: 12px;">⏳ PRE-RESERVA</span></td>
                        </tr>
                    </table>
                </div>
                
                <div class="highlight">
                    <div style="color: #666; font-size: 14px;">Monto Total</div>
                    <div class="amount">${reserva.monto_total} {reserva.moneda}</div>
                </div>
                
                {"<div class='section'><div class='section-title'>💬 Comentarios del Cliente</div><p style='background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 0;'>" + str(reserva.comentarios_cliente) + "</p></div>" if reserva.comentarios_cliente else ""}
                
                <div style="text-align: center; margin-top: 25px;">
                    <a href="https://www.mirlotoursec.com/admin/reservas/{reserva.id}" class="btn">
                        👁️ Ver en Panel de Admin
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>Reserva creada el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    enviar_email(
        [admin_email],
        f"🔔 Nueva Pre-Reserva #{reserva.id} - {tour.nombre} - {usuario.nombre}",
        html_content
    )

    # ================== GUÍAS PÚBLICOS =====================

@tour_bp.get("/guias")
def public_list_guias():
    """Lista pública de guías activos para mostrar en el frontend"""
    guias = Guia.query.filter_by(activo=True).order_by(Guia.nombre.asc()).all()

    return jsonify([
        {
            "id": g.id,
            "nombre": g.nombre,
            "foto_url": g.foto_url,
            "especialidad": g.especialidad,
            "bio": g.bio,
            "idiomas": g.idiomas,
            "pais_base": g.pais_base,
        }
        for g in guias
    ])


# ================== UBICACIONES PUBLICAS (PARA MAPAS) =====================

@tour_bp.get("/<slug>/ubicaciones")
def get_tour_ubicaciones(slug):
    """
    Obtiene las ubicaciones de un tour para mostrar en un mapa.
    URL: /tours/<slug>/ubicaciones

    Respuesta ideal para usar con Leaflet, Google Maps, Mapbox, etc.
    """
    tour = Tour.query.filter_by(slug=slug, activo=True).first()
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    ubicaciones = TourUbicacion.query.filter_by(
        tour_id=tour.id,
        activo=True
    ).order_by(TourUbicacion.orden.asc()).all()

    # Calcular centro del mapa (promedio de coordenadas)
    coords_validas = [
        (float(u.latitud), float(u.longitud))
        for u in ubicaciones
        if u.latitud and u.longitud
    ]

    centro = None
    if coords_validas:
        lat_promedio = sum(c[0] for c in coords_validas) / len(coords_validas)
        lng_promedio = sum(c[1] for c in coords_validas) / len(coords_validas)
        centro = {"lat": lat_promedio, "lng": lng_promedio}

    return jsonify({
        "tour": {
            "id": tour.id,
            "nombre": tour.nombre,
            "slug": tour.slug,
            "pais": tour.pais,
        },
        "centro": centro,
        "zoom_sugerido": 7 if len(ubicaciones) > 3 else 10,
        "ubicaciones": [u.to_dict() for u in ubicaciones],
        # Formato GeoJSON para compatibilidad con librerias de mapas
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": u.id,
                        "nombre": u.nombre,
                        "descripcion": u.descripcion,
                        "orden": u.orden,
                        "tipo": u.tipo_ubicacion,
                        "dia_inicio": u.dia_inicio,
                        "dia_fin": u.dia_fin,
                        "imagen_url": u.imagen_url,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(u.longitud), float(u.latitud)]
                    } if u.latitud and u.longitud else None
                }
                for u in ubicaciones
            ]
        }
    })