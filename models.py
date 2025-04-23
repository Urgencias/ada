from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import case
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from enum import Enum as PyEnum
import logging

logger = logging.getLogger(__name__)

# Enum para estados de llamadas
class EstadoLlamadaEnum(PyEnum):
    PENDIENTE = "PENDIENTE"
    PROGRAMADA = "PROGRAMADA"
    EN_CURSO = "EN_CURSO"
    COMPLETADA = "COMPLETADA"
    FALLIDA = "FALLIDA"
    FALLIDA_PERMANENTE = "FALLIDA_PERMANENTE"
    CANCELADA = "CANCELADA"
    ERROR = "ERROR"
    # Se elimina el estado INICIADA ya que ahora usamos EN_CURSO

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    email_verificado = Column(Boolean, default=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    es_admin = Column(Boolean, default=False)
    llamadas_disponibles = Column(Integer, default=100)
    llamadas_realizadas = Column(Integer, default=0)

    # Relación con recordatorios
    recordatorios = relationship("Recordatorio",
                                back_populates="user",
                                cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def puede_realizar_llamada(self) -> bool:
        if self.es_admin:
            return True
        return self.llamadas_disponibles > self.llamadas_realizadas

    def registrar_llamada(self):
        if not self.es_admin:
            self.llamadas_realizadas += 1
            db.session.commit()

    def renovar_llamadas(self):
        if not self.es_admin:
            self.llamadas_realizadas = 0
            self.llamadas_disponibles = 100
            db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'

class Recordatorio(db.Model):
    __tablename__ = 'recordatorios'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,
                     ForeignKey('users.id', ondelete='CASCADE'),
                     nullable=False)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False)
    fecha = Column(DateTime, nullable=False)
    hora = Column(String(5), nullable=False)  # Format: "HH:MM"
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(50), default='personal')
    repeticion = Column(Integer, default=0)
    siguiente_llamada = Column(DateTime, nullable=True)

    # Relación con usuarios y registros de llamadas
    user = relationship("User", back_populates="recordatorios")
    registros = relationship("RegistroLlamada",
                             back_populates="recordatorio",
                             cascade='all, delete-orphan')

    @classmethod
    def get_recordatorios_ordenados(cls, user_id):
        """Obtiene los recordatorios ordenados por fecha y hora para un usuario"""
        return cls.query.filter_by(user_id=user_id)\
                   .order_by(cls.fecha.asc(), cls.hora.asc())\
                   .all()

    def __repr__(self):
        return f'<Recordatorio {self.id}: {self.nombre}>'

class RegistroLlamada(db.Model):
    __tablename__ = 'registros_llamadas'
    id = Column(Integer, primary_key=True)
    recordatorio_id = Column(Integer,
                          ForeignKey('recordatorios.id', ondelete='CASCADE'),
                          nullable=False)
    estado = Column(Enum(EstadoLlamadaEnum),
                   nullable=False,
                   default=EstadoLlamadaEnum.PENDIENTE)
    intentos = Column(Integer, default=0)
    fecha_llamada = Column(DateTime, default=datetime.utcnow)
    siguiente_intento = Column(DateTime, nullable=True)
    error_mensaje = Column(Text, nullable=True)
    duracion = Column(Integer, default=0)  # Duración en segundos
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con recordatorios
    recordatorio = relationship("Recordatorio", back_populates="registros")

    def registrar_intento(self, exito: bool, mensaje_error: str = None):
        try:
            self.intentos += 1
            if exito:
                self.estado = EstadoLlamadaEnum.COMPLETADA
            else:
                self.estado = EstadoLlamadaEnum.PENDIENTE
                if mensaje_error:
                    self.error_mensaje = mensaje_error

            db.session.commit()
        except Exception as e:
            logger.error(f"Error al registrar intento de llamada: {str(e)}")
            db.session.rollback()
            raise

    def __repr__(self):
        return f'<RegistroLlamada {self.id}: {self.estado}>'

class NotificacionLlamada(db.Model):
    __tablename__ = 'notificaciones_llamadas'
    id = Column(Integer, primary_key=True)
    registro_llamada_id = Column(Integer,
                                 ForeignKey('registros_llamadas.id',
                                            ondelete='CASCADE'),
                                 nullable=False)
    mensaje = Column(Text, nullable=False)
    nivel = Column(String(20), default='info')  # info, warning, error, success
    leida = Column(Boolean, default=False)

    # Relación con registros de llamada
    registro_llamada = relationship("RegistroLlamada",
                                    backref="notificaciones")

    def __repr__(self):
        return f'<NotificacionLlamada {self.id}: {self.nivel}>'

class Contador(db.Model):
    __tablename__ = 'contadores'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    llamadas_totales = Column(Integer, nullable=False, default=0)
    llamadas_completadas = Column(Integer, nullable=False, default=0)
    llamadas_pendientes = Column(Integer, nullable=False, default=0)
    llamadas_en_curso = Column(Integer, nullable=False, default=0)
    llamadas_error = Column(Integer, nullable=False, default=0)
    ultima_actualizacion = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con el usuario
    usuario = relationship("User", backref=backref("contador", uselist=False, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Contador {self.id}: Usuario {self.usuario_id}>'

    @classmethod
    def inicializar_contador(cls, usuario_id):
        """Asegura que existe un contador para el usuario especificado"""
        try:
            contador = cls.query.filter_by(usuario_id=usuario_id).first()
            if not contador:
                contador = cls(
                    usuario_id=usuario_id,
                    ultima_actualizacion=datetime.utcnow()
                )
                db.session.add(contador)
                db.session.commit()
                logger.info(f"Contador inicializado para usuario {usuario_id}")
            return contador
        except Exception as e:
            logger.error(f"Error al inicializar contador para usuario {usuario_id}: {str(e)}")
            db.session.rollback()
            raise

    @classmethod
    def actualizar_contador(cls, usuario_id, completadas=0, pendientes=0, en_curso=0, error=0):
        """Actualiza los contadores específicos para un usuario"""
        try:
            contador = cls.inicializar_contador(usuario_id)

            # Actualizar contadores solo si hay cambios
            if completadas: contador.llamadas_completadas += completadas
            if pendientes: contador.llamadas_pendientes += pendientes
            if en_curso: contador.llamadas_en_curso += en_curso
            if error: contador.llamadas_error += error

            # Actualizar el total y la fecha
            contador.llamadas_totales = (
                contador.llamadas_completadas + 
                contador.llamadas_pendientes + 
                contador.llamadas_en_curso + 
                contador.llamadas_error
            )
            contador.ultima_actualizacion = datetime.utcnow()

            db.session.commit()
            logger.info(f"Contador actualizado para usuario {usuario_id}")
            return contador
        except Exception as e:
            logger.error(f"Error al actualizar contador para usuario {usuario_id}: {str(e)}")
            db.session.rollback()
            raise

    @classmethod
    def reiniciar_contador(cls, usuario_id):
        """Reinicia todos los contadores para un usuario"""
        try:
            contador = cls.inicializar_contador(usuario_id)
            contador.llamadas_totales = 0
            contador.llamadas_completadas = 0
            contador.llamadas_pendientes = 0
            contador.llamadas_en_curso = 0
            contador.llamadas_error = 0
            contador.ultima_actualizacion = datetime.utcnow()

            db.session.commit()
            logger.info(f"Contador reiniciado para usuario {usuario_id}")
            return contador
        except Exception as e:
            logger.error(f"Error al reiniciar contador para usuario {usuario_id}: {str(e)}")
            db.session.rollback()
            raise