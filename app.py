# app.py
import os
from flask import Flask, jsonify, send_from_directory

from config import Config
from extensions import db, jwt, cors, mail  # ⭐ Agregar mail
from routes.consulta_routes import consulta_bp

# imports de rutas
import routes.auth_routes as auth_routes
import routes.tour_routes as tour_routes
import routes.reservation_routes as reservation_routes
import routes.admin_routes as admin_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

    # Crear carpeta de uploads si no existe
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ⭐ CONFIGURACIÓN DE CORREO (Flask-Mail)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.environ.get('GMAIL_SMTP_USER', 'Salesmirlotours@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('GMAIL_SMTP_APP_PASSWORD', 'xjzq ybas kmfd nzvu')
    app.config['MAIL_DEFAULT_SENDER'] = ('Mirlo Tours', os.environ.get('GMAIL_SMTP_USER', 'Salesmirlotours@gmail.com'))
    app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'Salesmirlotours@gmail.com')  # Correo del admin

    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    # Configuración CORS mejorada
    cors_origins = app.config["CORS_ORIGINS"]
    if cors_origins == "*":
        origins_list = "*"
    else:
        origins_list = [o.strip() for o in cors_origins.split(",")]

    cors(app, resources={r"/*": {
        "origins": origins_list,
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True if origins_list != "*" else False
    }})
    mail.init_app(app)  # ⭐ Inicializar mail

    # Registrar blueprints
    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(tour_routes.tour_bp)
    app.register_blueprint(reservation_routes.reservation_bp)
    app.register_blueprint(admin_routes.admin_bp)
    app.register_blueprint(consulta_bp)

    # Ruta de salud
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # 📸 Servir archivos subidos (uploads)
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, threaded=True,use_reloader=False)