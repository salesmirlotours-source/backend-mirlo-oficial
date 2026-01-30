# models.py
from datetime import datetime
from enum import Enum
import enum

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum as PgEnum, Numeric
from sqlalchemy.orm import relationship, backref

from extensions import db


# -----------------------
# ENUMS (Python + DB)
# -----------------------

class RolUsuario(str, Enum):
    CLIENTE = "cliente"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class NivelActividad(str, Enum):
    BAJA = "baja"
    MODERADA = "moderada"
    ALTA = "alta"


class FechaEstado(str, Enum):
    ABIERTA = "abierta"
    LLENA = "llena"
    CERRADA = "cerrada"
    CANCELADA = "cancelada"


class ReservaEstado(str, Enum):
    PRE_RESERVA = "pre_reserva"
    CONFIRMADA = "confirmada"
    CANCELADA_CLIENTE = "cancelada_cliente"
    CANCELADA_OPERADOR = "cancelada_operador"


class PagoEstado(str, Enum):
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    REEMBOLSO_PARCIAL = "reembolso_parcial"
    REEMBOLSO_TOTAL = "reembolso_total"
    SIN_REEMBOLSO = "sin_reembolso"


class SeccionTipo(str, Enum):
    CONSEJOS = "consejos_generales"
    QUE_LLEVAR = "que_llevar"
    EQUIPO = "equipo_fotografico"
    VESTIMENTA = "vestimenta"
    CLIMA = "clima"
    POLITICAS = "politicas_generales"
    POLITICAS_CANCEL = "politicas_cancelacion"
    OTROS = "otros"


class IncluyeTipo(str, Enum):
    INCLUYE = "incluye"
    NO_INCLUYE = "no_incluye"


class ComentarioEstado(str, Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


# -----------------------
# MODELOS
# -----------------------

class Categoria(db.Model):
    __tablename__ = "categorias"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(500))
    icono = db.Column(db.String(50))
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    tours = relationship("Tour", backref="categoria", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "slug": self.slug,
            "descripcion": self.descripcion,
            "imagen_url": self.imagen_url,
            "icono": self.icono,
            "orden": self.orden,
            "activo": self.activo,
        }

    def to_dict_with_tours(self):
        return {
            **self.to_dict(),
            "tours": [
                {
                    "id": t.id,
                    "nombre": t.nombre,
                    "slug": t.slug,
                    "foto_portada": t.foto_portada,
                    "precio_pp": float(t.precio_pp) if t.precio_pp else None,
                    "duracion_dias": t.duracion_dias,
                }
                for t in self.tours if t.activo
            ],
            "total_tours": len([t for t in self.tours if t.activo])
        }


class Usuario(db.Model):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    email = db.Column(db.String(255), nullable=False, unique=True)
    telefono = db.Column(db.String(50))
    pais = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="cliente")

    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    reservas = relationship("Reserva", backref="usuario", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "telefono": self.telefono,
            "pais": self.pais,
            "rol": self.rol,
            "activo": self.activo,
        }


class Guia(db.Model):
    __tablename__ = "guias"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    foto_url = db.Column(db.Text)
    bio = db.Column(db.Text)
    especialidad = db.Column(db.String(150))
    idiomas = db.Column(db.String(255))
    pais_base = db.Column(db.String(100))
    redes_sociales = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Tour(db.Model):
    __tablename__ = "tours"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True)
    pais = db.Column(db.String(100), nullable=False)
    categoria_id = db.Column(db.BigInteger, db.ForeignKey("travel.categorias.id", ondelete="SET NULL"))
    duracion_dias = db.Column(db.Integer, nullable=False)
    nivel_actividad = db.Column(db.String(20))  # 'baja', 'moderada', 'alta'
  # 'baja', 'moderada', 'alta'
    guias_extra = relationship("TourGuia", backref="tour_ref", lazy=True)
    precio_pp = db.Column(Numeric(10, 2))
    moneda = db.Column(db.String(10), default="USD")
    banner_url = db.Column(db.Text)
    descripcion_corta = db.Column(db.Text)
    descripcion_larga = db.Column(db.Text)
    ruta_resumida = db.Column(db.Text)
    guia_principal_id = db.Column(db.BigInteger, db.ForeignKey("travel.guias.id"))
    guia_principal = relationship("Guia", foreign_keys=[guia_principal_id])
    foto_portada = db.Column(db.Text)  # ⭐ AGREGAR ESTA LÍNEA
    activo = db.Column(db.Boolean, nullable=False, default=True)
    orden_destacado = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    fechas = relationship("FechaTour", backref="tour", lazy=True)
    itinerarios = relationship("Itinerario", backref="tour", lazy=True)
    galerias = relationship("Galeria", backref="tour", lazy=True)
    secciones = relationship("TourSeccion", backref="tour", lazy=True)
    incluye_items = relationship("TourIncluye", backref="tour", lazy=True)
    comentarios = relationship("Comentario", backref="tour", lazy=True)
    ubicaciones = relationship("TourUbicacion", backref="tour", lazy=True)


    def to_card_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "slug": self.slug,
            "pais": self.pais,
            "duracion_dias": self.duracion_dias,
            "nivel_actividad": self.nivel_actividad,
            "precio_pp": float(self.precio_pp) if self.precio_pp else None,
            "moneda": self.moneda,
            "banner_url": self.banner_url,
            "foto_portada": self.foto_portada,
            "categoria": {
                "id": self.categoria.id,
                "nombre": self.categoria.nombre,
                "slug": self.categoria.slug,
            } if self.categoria else None,
        }

    def to_detail_dict(self):
        return {
            **self.to_card_dict(),
            "descripcion_corta": self.descripcion_corta,
            "descripcion_larga": self.descripcion_larga,
            "ruta_resumida": self.ruta_resumida,
            "fechas": [f.to_dict() for f in self.fechas],
            "itinerarios": [i.to_dict() for i in self.itinerarios],
            "galeria": [g.to_dict() for g in self.galerias],
            "secciones": [s.to_dict() for s in self.secciones],
            "incluye": [i.to_dict() for i in self.incluye_items],

            "guia_principal": {
                "id": self.guia_principal.id,
                "nombre": self.guia_principal.nombre,
                "foto": self.guia_principal.foto_url,
                "bio": self.guia_principal.bio,
                "especialidad": self.guia_principal.especialidad,
                "idiomas": self.guia_principal.idiomas,
                "pais_base": self.guia_principal.pais_base
            } if self.guia_principal else None,

            "guias_equipo": [
                {
                    "guia_id": tg.guia.id,
                    "nombre": tg.guia.nombre,
                    "foto": tg.guia.foto_url,
                    "especialidad": tg.guia.especialidad,
                    "rol_en_tour": tg.rol
                } for tg in self.guias_extra
            ],

            "banners": [b.to_dict() for b in self.banners.filter_by(activo=True).order_by(TourBanner.orden).all()],

            # Ubicaciones para el mapa
            "ubicaciones": sorted(
                [u.to_dict() for u in self.ubicaciones if u.activo],
                key=lambda x: x["orden"] or 0
            ),
        }



class TourGuia(db.Model):
    __tablename__ = "tour_guias"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    guia_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.guias.id", ondelete="CASCADE"),
        nullable=False,
    )
    rol = db.Column(db.String(100))
    guia = relationship("Guia")
class FechaTour(db.Model):
    __tablename__ = "fechas_tour"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    cupos_totales = db.Column(db.Integer, nullable=False, default=0)
    cupos_ocupados = db.Column(db.Integer, nullable=False, default=0)
    
    # --- CAMBIO CRÍTICO AQUÍ ---
    # Usamos db.String para que pase el texto "abierta" tal cual, sin convertirlo a mayúsculas.
    # Postgres validará que sea correcto de todas formas.
    estado = db.Column(
        db.String(50), 
        nullable=False,
        default="abierta", 
    )
    # ---------------------------

    notas = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    reservas = relationship("Reserva", backref="fecha_tour", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "fecha_inicio": self.fecha_inicio.isoformat(),
            "fecha_fin": self.fecha_fin.isoformat(),
            "cupos_totales": self.cupos_totales,
            "cupos_ocupados": self.cupos_ocupados,
            # Al ser string, ya no necesitamos .value, devolvemos directo
            "estado": self.estado, 
        }

class Itinerario(db.Model):
    __tablename__ = "itinerarios"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    orden_dia = db.Column(db.Integer, nullable=False)
    titulo_dia = db.Column(db.String(255), nullable=False)
    descripcion_dia = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "orden_dia": self.orden_dia,
            "titulo_dia": self.titulo_dia,
            "descripcion_dia": self.descripcion_dia,
        }


class Galeria(db.Model):
    __tablename__ = "galerias"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    categoria = db.Column(db.String(100))
    foto_url = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text)
    orden = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "foto_url": self.foto_url,
            "descripcion": self.descripcion,
            "orden": self.orden,
        }

class TourSeccion(db.Model):
    __tablename__ = "tour_secciones"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )

    # --- CAMBIO: Usamos String ---
    tipo = db.Column(db.String(50), nullable=False)
    # -----------------------------

    titulo = db.Column(db.String(255), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            # --- CAMBIO: Quitamos .value
            "tipo": self.tipo,
            "titulo": self.titulo,
            "contenido": self.contenido,
            "orden": self.orden,
        }

class TourIncluye(db.Model):
    __tablename__ = "tour_incluye"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # --- CAMBIO: Usamos String para evitar error de mayúsculas ---
    tipo = db.Column(db.String(50), nullable=False)
    # -----------------------------------------------------------

    descripcion = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            # --- CAMBIO: Quitamos .value porque ahora es un string directo
            "tipo": self.tipo, 
            "descripcion": self.descripcion,
            "orden": self.orden,
        }

class ConsultaTour(db.Model):
    __tablename__ = "consultas_tour"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.usuarios.id", ondelete="SET NULL"),
    )
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(50))
    mensaje = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(50), nullable=False, default="nuevo")
    notas_internas = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Reserva(db.Model):
    __tablename__ = "reservas"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.fechas_tour.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numero_personas = db.Column(db.Integer, nullable=False, default=1)
    estado_reserva = db.Column(
        PgEnum(ReservaEstado, name="reserva_estado"),
        nullable=False,
        default=ReservaEstado.PRE_RESERVA,
    )
    estado_pago = db.Column(
        PgEnum(PagoEstado, name="pago_estado"),
        nullable=False,
        default=PagoEstado.PENDIENTE,
    )

    monto_total = db.Column(Numeric(10, 2))
    moneda = db.Column(db.String(10), default="USD")

    metodo_pago_externo = db.Column(db.String(100))
    referencia_pago = db.Column(db.String(255))
    fecha_pago = db.Column(db.Date)

    monto_reembolso = db.Column(Numeric(10, 2))
    penalidad_porcentaje = db.Column(Numeric(5, 2))
    motivo_cancelacion = db.Column(db.Text)
    fecha_cancelacion = db.Column(db.Date)

    comentarios_cliente = db.Column(db.Text)
    comentarios_internos = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    tour = relationship("Tour", backref=backref("reservas", lazy=True))

    def to_dict_public(self):
        return {
            "id": self.id,
            "tour_id": self.tour_id,
            "fecha_tour_id": self.fecha_tour_id,
            "numero_personas": self.numero_personas,
            "estado_reserva": self.estado_reserva.value,
            "estado_pago": self.estado_pago.value,
            "monto_total": float(self.monto_total) if self.monto_total else None,
            "moneda": self.moneda,
            "created_at": self.created_at.isoformat(),
        }


class Comentario(db.Model):
    __tablename__ = "comentarios"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    usuario_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )

    calificacion = db.Column(db.Integer)
    comentario = db.Column(db.Text, nullable=False)

    estado = db.Column(
        PgEnum(ComentarioEstado, name="comentario_estado"),
        nullable=False,
        default=ComentarioEstado.PENDIENTE,
    )
    respuesta_admin = db.Column(db.Text)

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    usuario = relationship("Usuario", backref=backref("comentarios", lazy=True))

    def to_public_dict(self):
        return {
            "id": self.id,
            "usuario": self.usuario.nombre if self.usuario else None,
            "calificacion": self.calificacion,
            "comentario": self.comentario,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MediaTipo(enum.Enum):
    imagen = "imagen"  # ← minúsculas
    video = "video"    # ← minúsculas


class TourUbicacion(db.Model):
    """
    Ubicaciones/lugares que se visitan en cada tour.
    Permite mostrar un mapa con la ruta del tour.
    """
    __tablename__ = "tour_ubicaciones"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(
        db.BigInteger,
        db.ForeignKey("travel.tours.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Informacion geografica
    nombre = db.Column(db.String(255), nullable=False)
    pais = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(150))
    ciudad = db.Column(db.String(150))
    descripcion = db.Column(db.Text)

    # Coordenadas para el mapa
    latitud = db.Column(Numeric(10, 8))
    longitud = db.Column(Numeric(11, 8))

    # Orden de visita
    orden = db.Column(db.Integer, default=1)

    # Dias del itinerario
    dia_inicio = db.Column(db.Integer)
    dia_fin = db.Column(db.Integer)

    # Tipo de ubicacion
    tipo_ubicacion = db.Column(db.String(50), default="destino")

    # Imagen opcional
    imagen_url = db.Column(db.Text)

    # Activo
    activo = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tour_id": self.tour_id,
            "nombre": self.nombre,
            "pais": self.pais,
            "provincia": self.provincia,
            "ciudad": self.ciudad,
            "descripcion": self.descripcion,
            "latitud": float(self.latitud) if self.latitud else None,
            "longitud": float(self.longitud) if self.longitud else None,
            "orden": self.orden,
            "dia_inicio": self.dia_inicio,
            "dia_fin": self.dia_fin,
            "tipo_ubicacion": self.tipo_ubicacion,
            "imagen_url": self.imagen_url,
            "activo": self.activo,
        }


class TourBanner(db.Model):
    """
    Banners/portadas dinámicas para tours.
    Soporta imágenes y videos, con configuración de carrusel.
    """
    __tablename__ = "tour_banners"
    __table_args__ = {"schema": "travel"}

    id = db.Column(db.BigInteger, primary_key=True)
    tour_id = db.Column(db.BigInteger, db.ForeignKey("travel.tours.id", ondelete="CASCADE"), nullable=False)

    # Tipo de media
    tipo = db.Column(db.Enum(MediaTipo, schema="travel"), nullable=False, default=MediaTipo.imagen)

    # URLs
    media_url = db.Column(db.Text, nullable=False)  # URL de imagen o video
    poster_url = db.Column(db.Text)  # Preview para videos

    # Contenido opcional sobre el banner
    titulo = db.Column(db.Text)
    subtitulo = db.Column(db.Text)
    texto_boton = db.Column(db.Text)

    # Configuración
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    es_principal = db.Column(db.Boolean, default=False)

    # Visual
    overlay_opacity = db.Column(db.Numeric(3, 2), default=0.35)
    posicion_vertical = db.Column(db.String(20), default="center")  # top, center, bottom

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relación
    tour = db.relationship("Tour", backref=db.backref("banners", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "tour_id": self.tour_id,
            "tipo": self.tipo.value if self.tipo else "imagen",
            "media_url": self.media_url,
            "poster_url": self.poster_url,
            "titulo": self.titulo,
            "subtitulo": self.subtitulo,
            "texto_boton": self.texto_boton,
            "orden": self.orden,
            "activo": self.activo,
            "es_principal": self.es_principal,
            "overlay_opacity": float(self.overlay_opacity) if self.overlay_opacity else 0.35,
            "posicion_vertical": self.posicion_vertical or "center",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

























































