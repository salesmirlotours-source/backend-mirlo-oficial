# routes/auth_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from extensions import db
from models import Usuario, RolUsuario

print(">>> Cargando routes.auth_routes")  # DEBUG

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

print(">>> auth_bp creado en auth_routes:", auth_bp)  # DEBUG
@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    required = ["nombre", "email", "password"]
    if not all(field in data for field in required):
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"message": "El email ya está registrado"}), 400

    user = Usuario(
        nombre=data["nombre"],
        apellido=data.get("apellido"),
        email=data["email"],
        telefono=data.get("telefono"),
        pais=data.get("pais"),
        rol="cliente",  # valor en minúsculas

    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token
    }), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email y password son obligatorios"}), 400

    user = Usuario.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Credenciales incorrectas"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "user": user.to_dict(),
        "access_token": access_token
    })


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404
    return jsonify({"user": user.to_dict()})

# En auth_routes.py

@auth_bp.get("/verify")
@jwt_required()
def verify_token():
    """Verifica si el token JWT es válido"""
    try:
        user_id = get_jwt_identity()
        user = Usuario.query.get(user_id)
        
        if not user:
            return jsonify({"valid": False, "message": "Usuario no encontrado"}), 401
        
        if not user.activo:
            return jsonify({"valid": False, "message": "Usuario desactivado"}), 401
        
        return jsonify({
            "valid": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "rol": user.rol
            }
        }), 200
        
    except Exception as e:
        return jsonify({"valid": False, "message": str(e)}), 401


@auth_bp.put("/perfil")
@jwt_required()
def update_perfil():
    """Actualiza el perfil del usuario autenticado."""
    user_id = get_jwt_identity()
    user = Usuario.query.get(user_id)
    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404

    data = request.get_json() or {}

    campos_permitidos = ["nombre", "apellido", "telefono", "pais"]
    for campo in campos_permitidos:
        if campo in data:
            setattr(user, campo, data[campo])

    # Cambio de contraseña (opcional)
    if data.get("password_actual") and data.get("password_nueva"):
        if not user.check_password(data["password_actual"]):
            return jsonify({"message": "La contraseña actual es incorrecta"}), 400
        user.set_password(data["password_nueva"])

    db.session.commit()

    return jsonify({
        "message": "Perfil actualizado correctamente",
        "user": user.to_dict()
    })