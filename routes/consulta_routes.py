# =====================================================
# AGREGAR A tour_routes.py o crear consulta_routes.py
# =====================================================

from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from extensions import db, mail
from models import Tour
from datetime import datetime

consulta_bp = Blueprint("consulta", __name__, url_prefix="/tours")


@consulta_bp.post("/<slug>/consulta")
def crear_consulta(slug):
    """
    Recibe una consulta del formulario de contacto y envía correos:
    1. Al admin notificando la consulta
    2. Al cliente confirmando que recibimos su mensaje
    """
    data = request.get_json() or {}

    # Validar campos requeridos
    required = ["nombre", "email", "telefono", "mensaje"]
    for field in required:
        if not data.get(field):
            return jsonify({"message": f"El campo '{field}' es obligatorio"}), 400

    # Validar email
    import re
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, data["email"]):
        return jsonify({"message": "El email no es válido"}), 400

    # Obtener info del tour (opcional)
    tour = Tour.query.filter_by(slug=slug).first()
    tour_nombre = tour.nombre if tour else data.get("tour_nombre", slug)

    # Preparar datos
    nombre = data["nombre"]
    email = data["email"]
    telefono = data["telefono"]
    mensaje = data["mensaje"]
    fecha_consulta = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        # ========== 1. CORREO AL ADMIN ==========
        admin_email = current_app.config.get('ADMIN_EMAIL', 'Salesmirlotours@gmail.com')
        
        msg_admin = Message(
            subject=f"📩 Nueva Consulta - {tour_nombre}",
            recipients=[admin_email],
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #C1A919 0%, #8B7A12 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">📩 Nueva Consulta Recibida</h1>
                    </div>
                    
                    <!-- Contenido -->
                    <div style="padding: 30px;">
                        
                        <!-- Info del Tour -->
                        <div style="background: #fffaf0; border-left: 4px solid #C1A919; padding: 15px; margin-bottom: 25px; border-radius: 0 10px 10px 0;">
                            <p style="margin: 0; color: #666;">Tour consultado:</p>
                            <p style="margin: 5px 0 0; font-size: 1.2rem; font-weight: bold; color: #333;">{tour_nombre}</p>
                        </div>
                        
                        <!-- Datos del Cliente -->
                        <h3 style="color: #333; border-bottom: 2px solid #C1A919; padding-bottom: 10px;">👤 Datos del Cliente</h3>
                        
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
                            <tr>
                                <td style="padding: 12px; background: #f9f9f9; font-weight: bold; width: 30%;">Nombre:</td>
                                <td style="padding: 12px; background: #f9f9f9;">{nombre}</td>
                            </tr>
                            <tr>
                                <td style="padding: 12px; font-weight: bold;">Email:</td>
                                <td style="padding: 12px;">
                                    <a href="mailto:{email}" style="color: #C1A919;">{email}</a>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px; background: #f9f9f9; font-weight: bold;">Teléfono:</td>
                                <td style="padding: 12px; background: #f9f9f9;">
                                    <a href="tel:{telefono}" style="color: #C1A919;">{telefono}</a>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 12px; font-weight: bold;">Fecha:</td>
                                <td style="padding: 12px;">{fecha_consulta}</td>
                            </tr>
                        </table>
                        
                        <!-- Mensaje -->
                        <h3 style="color: #333; border-bottom: 2px solid #C1A919; padding-bottom: 10px;">💬 Mensaje</h3>
                        <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                            <p style="margin: 0; line-height: 1.6; color: #444; white-space: pre-wrap;">{mensaje}</p>
                        </div>
                        
                        <!-- Botones de Acción -->
                        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                            <a href="mailto:{email}?subject=Re: Consulta sobre {tour_nombre}" 
                               style="display: inline-block; background: #C1A919; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                                ✉️ Responder por Email
                            </a>
                            <a href="https://wa.me/{telefono.replace(' ', '').replace('-', '').replace('+', '')}?text=Hola {nombre.split()[0]}! Gracias por contactar a Mirlo Tours." 
                               style="display: inline-block; background: #25D366; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold;">
                                📱 WhatsApp
                            </a>
                        </div>
                        
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: #333; color: #999; padding: 20px; text-align: center; font-size: 12px;">
                        <p style="margin: 0;">Este correo fue enviado automáticamente desde el formulario de contacto de Mirlo Tours</p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
        )
        mail.send(msg_admin)
        print(f"📧 Correo admin enviado a: {admin_email}")

        # ========== 2. CORREO AL CLIENTE (Confirmación) ==========
        msg_cliente = Message(
            subject=f"Recibimos tu consulta - Mirlo Tours 🦅",
            recipients=[email],
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 40px; text-align: center;">
                        <img src="https://mirlotours.com/logo.png" alt="Mirlo Tours" style="max-width: 150px; margin-bottom: 20px;">
                        <h1 style="color: #C1A919; margin: 0; font-size: 28px;">¡Gracias por contactarnos!</h1>
                    </div>
                    
                    <!-- Contenido -->
                    <div style="padding: 40px 30px;">
                        
                        <p style="font-size: 1.1rem; color: #333; margin-bottom: 25px;">
                            Hola <strong>{nombre.split()[0]}</strong>,
                        </p>
                        
                        <p style="color: #555; line-height: 1.7;">
                            Hemos recibido tu consulta sobre <strong style="color: #C1A919;">{tour_nombre}</strong>. 
                            Nuestro equipo la revisará y te responderemos en menos de <strong>24 horas</strong>.
                        </p>
                        
                        <!-- Resumen de la consulta -->
                        <div style="background: #fffaf0; border-radius: 10px; padding: 20px; margin: 25px 0; border: 1px solid #f0e6c8;">
                            <h3 style="color: #C1A919; margin: 0 0 15px 0; font-size: 1rem;">📋 Tu consulta:</h3>
                            <p style="margin: 0; color: #666; font-style: italic; line-height: 1.6;">"{mensaje[:200]}{'...' if len(mensaje) > 200 else ''}"</p>
                        </div>
                        
                        <p style="color: #555; line-height: 1.7;">
                            Si necesitas una respuesta más rápida, no dudes en contactarnos por WhatsApp:
                        </p>
                        
                        <!-- Botón WhatsApp -->
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://wa.me/593985676029?text=Hola! Envié una consulta sobre {tour_nombre}" 
                               style="display: inline-block; background: #25D366; color: white; padding: 15px 35px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 1.1rem;">
                                📱 Escríbenos por WhatsApp
                            </a>
                        </div>
                        
                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                        
                        <p style="color: #888; font-size: 0.9rem; text-align: center;">
                            Mientras tanto, puedes explorar nuestros otros tours en 
                            <a href="https://mirlotours.com" style="color: #C1A919;">mirlotours.com</a>
                        </p>
                        
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: #1a1a2e; color: #888; padding: 25px; text-align: center;">
                        <p style="margin: 0 0 10px 0; font-size: 14px;">
                            <strong style="color: #C1A919;">Mirlo Tours</strong> - Turismo de Naturaleza
                        </p>
                        <p style="margin: 0; font-size: 12px;">
                            📍 Quito, Ecuador | 📱 +593 98 567 6029 | ✉️ Salesmirlotours@gmail.com
                        </p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
        )
        mail.send(msg_cliente)
        print(f"📧 Correo cliente enviado a: {email}")

        return jsonify({
            "message": "Consulta enviada exitosamente",
            "email_enviado": True
        }), 200

    except Exception as e:
        print(f"❌ Error enviando correo: {str(e)}")
        # Aún así devolvemos éxito si los datos son válidos
        # El admin puede revisar logs
        return jsonify({
            "message": "Consulta recibida. Te contactaremos pronto.",
            "email_enviado": False,
            "error_detalle": str(e)
        }), 200


