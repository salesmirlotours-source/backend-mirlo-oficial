# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
mail = Mail()  # ⭐ Agregar esta línea
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS
