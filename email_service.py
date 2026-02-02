# email_service.py
import os
import resend

# Configurar API key de Resend
resend.api_key = os.environ.get('RESEND_API_KEY', '')

# Email por defecto para enviar (debe ser verificado en Resend o usar onboarding@resend.dev)
DEFAULT_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'Salesmirlotours@gmail.com')


def enviar_email(to: list, subject: str, html: str, from_email: str = None):
    """
    Envía un email usando Resend API.

    Args:
        to: Lista de emails destinatarios
        subject: Asunto del correo
        html: Contenido HTML del correo
        from_email: Email remitente (opcional, usa DEFAULT_FROM_EMAIL si no se especifica)

    Returns:
        dict con resultado o None si falla
    """
    try:
        params = {
            "from": from_email or DEFAULT_FROM_EMAIL,
            "to": to if isinstance(to, list) else [to],
            "subject": subject,
            "html": html,
        }

        result = resend.Emails.send(params)
        print(f"✅ Email enviado a: {to}")
        return result
    except Exception as e:
        print(f"❌ Error enviando email: {str(e)}")
        return None


def enviar_email_admin(subject: str, html: str):
    """Envía un email al admin"""
    return enviar_email([ADMIN_EMAIL], subject, html)


def enviar_email_cliente(email_cliente: str, subject: str, html: str):
    """Envía un email a un cliente"""
    return enviar_email([email_cliente], subject, html)
