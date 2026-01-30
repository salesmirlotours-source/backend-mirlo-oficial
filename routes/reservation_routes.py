# routes/reservation_routes.py
from datetime import date, datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_mail import Message

from extensions import db, mail
from models import (
    Usuario, Tour, FechaTour, Reserva,
    ReservaEstado, PagoEstado, FechaEstado
)

reservation_bp = Blueprint("reservas", __name__)


# =====================================================
# CREAR PRE-RESERVA (CLIENTE) - CON ENVÍO DE CORREO
# =====================================================

@reservation_bp.post("/tours/<int:tour_id>/reservas")
@jwt_required()
def crear_pre_reserva(tour_id):
    """
    Crea una pre-reserva para un tour.
    El cliente selecciona fecha y número de personas.
    Se envía correo de confirmación al cliente y notificación al admin.
    """
    user_id = get_jwt_identity()
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    tour = Tour.query.get(tour_id)
    if not tour:
        return jsonify({"message": "Tour no encontrado"}), 404

    data = request.get_json() or {}

    # Validar campos requeridos
    if "fecha_tour_id" not in data:
        return jsonify({"message": "Debe seleccionar una fecha de salida"}), 400
    if "numero_personas" not in data:
        return jsonify({"message": "Debe indicar el número de personas"}), 400

    try:
        fecha_tour_id = int(data["fecha_tour_id"])
        numero_personas = int(data["numero_personas"])
    except (ValueError, TypeError):
        return jsonify({"message": "Datos inválidos"}), 400

    if numero_personas < 1:
        return jsonify({"message": "El número de personas debe ser al menos 1"}), 400

    # Verificar que la fecha pertenece al tour
    fecha = FechaTour.query.filter_by(id=fecha_tour_id, tour_id=tour.id).first()
    if not fecha:
        return jsonify({"message": "La fecha seleccionada no es válida para este tour"}), 400

    # Verificar disponibilidad de cupos
    cupos_disponibles = fecha.cupos_totales - (fecha.cupos_ocupados or 0)
    if numero_personas > cupos_disponibles:
        return jsonify({
            "message": f"No hay suficientes cupos. Disponibles: {cupos_disponibles}"
        }), 400

    # Calcular monto total
    precio_pp = float(tour.precio_pp) if tour.precio_pp else 0
    monto_total = data.get("monto_total") or (precio_pp * numero_personas)

    # Crear la reserva
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

    # Actualizar cupos ocupados
    fecha.cupos_ocupados = (fecha.cupos_ocupados or 0) + numero_personas

    db.session.add(reserva)
    db.session.commit()

    # ==================== ENVIAR CORREOS ====================
    correo_enviado = False
    try:
        enviar_correo_cliente(reserva, usuario, tour, fecha)
        enviar_correo_admin(reserva, usuario, tour, fecha)
        correo_enviado = True
    except Exception as e:
        current_app.logger.error(f"Error enviando correo: {str(e)}")

    return jsonify({
        "message": "Pre-reserva creada exitosamente." + (" Te hemos enviado un correo de confirmación." if correo_enviado else ""),
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


# =====================================================
# MIS RESERVAS (CLIENTE)
# =====================================================

@reservation_bp.get("/tours/mis-reservas")
@jwt_required()
def mis_reservas():
    """Lista todas las reservas del usuario logueado"""
    user_id = get_jwt_identity()
    reservas = Reserva.query.filter_by(usuario_id=user_id).order_by(Reserva.created_at.desc()).all()
    
    resultado = []
    for r in reservas:
        tour = Tour.query.get(r.tour_id)
        fecha = FechaTour.query.get(r.fecha_tour_id) if r.fecha_tour_id else None
        
        resultado.append({
            "id": r.id,
            "tour_id": r.tour_id,
            "tour_nombre": tour.nombre if tour else None,
            "tour_slug": tour.slug if tour else None,
            "fecha_inicio": fecha.fecha_inicio.isoformat() if fecha and fecha.fecha_inicio else None,
            "fecha_fin": fecha.fecha_fin.isoformat() if fecha and fecha.fecha_fin else None,
            "numero_personas": r.numero_personas,
            "estado_reserva": r.estado_reserva.value,
            "estado_pago": r.estado_pago.value,
            "monto_total": float(r.monto_total) if r.monto_total else None,
            "moneda": r.moneda,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    
    return jsonify(resultado)


# =====================================================
# OBTENER DETALLE DE MI RESERVA
# =====================================================

@reservation_bp.get("/reservas/<int:reserva_id>")
@jwt_required()
def get_mi_reserva(reserva_id):
    """
    Obtiene el detalle de una reserva específica del usuario logueado.
    Solo puede ver sus propias reservas.
    """
    user_id = get_jwt_identity()
    
    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404
    
    # Verificar que la reserva pertenece al usuario
    if reserva.usuario_id != int(user_id):
        return jsonify({"message": "No tienes permiso para ver esta reserva"}), 403
    
    # Obtener info adicional del tour y fecha
    tour = Tour.query.get(reserva.tour_id)
    fecha = FechaTour.query.get(reserva.fecha_tour_id) if reserva.fecha_tour_id else None
    
    return jsonify({
        "id": reserva.id,
        "tour_id": reserva.tour_id,
        "tour_nombre": tour.nombre if tour else None,
        "tour_slug": tour.slug if tour else None,
        "fecha_tour_id": reserva.fecha_tour_id,
        "fecha_inicio": fecha.fecha_inicio.isoformat() if fecha and fecha.fecha_inicio else None,
        "fecha_fin": fecha.fecha_fin.isoformat() if fecha and fecha.fecha_fin else None,
        "numero_personas": reserva.numero_personas,
        "estado_reserva": reserva.estado_reserva.value,
        "estado_pago": reserva.estado_pago.value,
        "monto_total": float(reserva.monto_total) if reserva.monto_total else None,
        "moneda": reserva.moneda,
        "metodo_pago_externo": reserva.metodo_pago_externo,
        "referencia_pago": reserva.referencia_pago,
        "fecha_pago": reserva.fecha_pago.isoformat() if reserva.fecha_pago else None,
        "monto_reembolso": float(reserva.monto_reembolso) if hasattr(reserva, 'monto_reembolso') and reserva.monto_reembolso else None,
        "motivo_cancelacion": reserva.motivo_cancelacion if hasattr(reserva, 'motivo_cancelacion') else None,
        "comentarios_cliente": reserva.comentarios_cliente,
        "created_at": reserva.created_at.isoformat() if reserva.created_at else None,
        "updated_at": reserva.updated_at.isoformat() if hasattr(reserva, 'updated_at') and reserva.updated_at else None,
    })


# =====================================================
# CANCELAR MI RESERVA
# =====================================================

@reservation_bp.patch("/reservas/<int:reserva_id>/cancelar")
@jwt_required()
def cancelar_mi_reserva(reserva_id):
    """
    Permite al cliente cancelar su propia reserva.
    Solo se puede cancelar si está en estado PRE_RESERVA o CONFIRMADA.
    """
    user_id = get_jwt_identity()
    
    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404
    
    # Verificar que la reserva pertenece al usuario
    if reserva.usuario_id != int(user_id):
        return jsonify({"message": "No tienes permiso para cancelar esta reserva"}), 403
    
    # Verificar que se puede cancelar
    if reserva.estado_reserva not in [ReservaEstado.PRE_RESERVA, ReservaEstado.CONFIRMADA]:
        return jsonify({"message": "Esta reserva ya no se puede cancelar"}), 400
    
    # Obtener datos para el motivo
    data = request.get_json() or {}
    motivo = data.get("motivo", "Cancelado por el cliente")
    
    # Liberar cupos
    if reserva.fecha_tour_id:
        fecha = FechaTour.query.get(reserva.fecha_tour_id)
        if fecha:
            fecha.cupos_ocupados = max(0, (fecha.cupos_ocupados or 0) - reserva.numero_personas)
    
    # Calcular reembolso si estaba pagado
    monto_reembolso = None
    if reserva.estado_pago == PagoEstado.PAGADO and reserva.monto_total:
        fecha = FechaTour.query.get(reserva.fecha_tour_id) if reserva.fecha_tour_id else None
        if fecha and fecha.fecha_inicio:
            dias_hasta_tour = (fecha.fecha_inicio - date.today()).days
            
            if dias_hasta_tour > 30:
                monto_reembolso = float(reserva.monto_total)
                reserva.estado_pago = PagoEstado.REEMBOLSO_TOTAL
            elif dias_hasta_tour > 15:
                monto_reembolso = float(reserva.monto_total) * 0.5
                reserva.estado_pago = PagoEstado.REEMBOLSO_PARCIAL
            else:
                monto_reembolso = 0
                # Sin reembolso, pero sigue como pagado
    
    # Actualizar estado
    reserva.estado_reserva = ReservaEstado.CANCELADA_CLIENTE
    reserva.motivo_cancelacion = motivo
    if hasattr(reserva, 'monto_reembolso'):
        reserva.monto_reembolso = monto_reembolso
    
    db.session.commit()
    
    return jsonify({
        "message": "Reserva cancelada correctamente",
        "reserva": {
            "id": reserva.id,
            "estado_reserva": reserva.estado_reserva.value,
            "estado_pago": reserva.estado_pago.value,
            "monto_reembolso": monto_reembolso,
        }
    })


# =====================================================
# ACTUALIZAR COMENTARIOS DE MI RESERVA
# =====================================================

@reservation_bp.patch("/reservas/<int:reserva_id>/comentarios")
@jwt_required()
def actualizar_comentarios_reserva(reserva_id):
    """
    Permite al cliente agregar/actualizar sus comentarios en la reserva.
    """
    user_id = get_jwt_identity()
    
    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"message": "Reserva no encontrada"}), 404
    
    if reserva.usuario_id != int(user_id):
        return jsonify({"message": "No tienes permiso"}), 403
    
    data = request.get_json() or {}
    
    if "comentarios_cliente" in data:
        reserva.comentarios_cliente = data["comentarios_cliente"]
    
    db.session.commit()
    
    return jsonify({
        "message": "Comentarios actualizados",
        "comentarios_cliente": reserva.comentarios_cliente
    })


# =====================================================
# FUNCIONES DE ENVÍO DE CORREO
# =====================================================

def enviar_correo_cliente(reserva, usuario, tour, fecha):
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
            .step {{ display: flex; align-items: center; margin: 10px 0; }}
            .step-num {{ background: #4CAF50; color: white; width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 10px; }}
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
                <p>Hola <strong>{usuario.nombre}</strong>,</p>
                
                <p>¡Gracias por elegirnos para tu próxima aventura! Hemos recibido tu solicitud de reserva para <strong>{tour.nombre}</strong>.</p>
                
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
                    <div class="step"><span class="step-num">1</span> Revisaremos tu solicitud (máximo 24 horas)</div>
                    <div class="step"><span class="step-num">2</span> Te contactaremos para confirmar disponibilidad</div>
                    <div class="step"><span class="step-num">3</span> Coordinaremos la forma de pago</div>
                    <div class="step"><span class="step-num">4</span> ¡Recibirás tu confirmación final!</div>
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
                <p>🌍 Especialistas en turismo de naturaleza en Ecuador</p>
                <p>📍 Ecuador | 📞 +593 98 567 6029 | ✉️ Salesmirlotours@gmail.com</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">
                <p style="font-size: 11px; color: #aaa;">
                    Este correo fue enviado porque solicitaste una reserva en nuestro sitio web.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg = Message(
        subject=f"✈️ Solicitud de Reserva #{reserva.id} - {tour.nombre}",
        recipients=[usuario.email],
        html=html_content
    )
    
    mail.send(msg)


def enviar_correo_admin(reserva, usuario, tour, fecha):
    """Envía notificación al admin sobre nueva pre-reserva"""
    
    admin_email = current_app.config.get('ADMIN_EMAIL', 'Salesmirlotours@gmail.com')
    
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
                    <strong>⚠️ Acción requerida:</strong> Un cliente ha solicitado una reserva que necesita tu confirmación.
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
                            <td>{getattr(usuario, 'telefono', None) or 'No proporcionado'}</td>
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
                            <td>Fecha de salida:</td>
                            <td>{fecha_inicio_str}</td>
                        </tr>
                        <tr>
                            <td>Fecha de regreso:</td>
                            <td>{fecha_fin_str}</td>
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
                    <a href="http://localhost:3000/admin/reservas/{reserva.id}" class="btn">
                        👁️ Ver en Panel de Admin
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>Reserva creada el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
                <p>Este es un correo automático del sistema de reservas.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg = Message(
        subject=f"🔔 Nueva Pre-Reserva #{reserva.id} - {tour.nombre} - {usuario.nombre}",
        recipients=[admin_email],
        html=html_content
    )
    
    mail.send(msg)