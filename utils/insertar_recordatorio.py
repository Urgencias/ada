import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from models import Recordatorio
from extensions import db
from flask_login import current_user

logger = logging.getLogger(__name__)

def insertar_recordatorio(datos: Dict) -> Tuple[bool, Optional[str], Optional[Recordatorio]]:
    """
    Inserta un nuevo recordatorio en la base de datos

    Args:
        datos: Diccionario con los datos del recordatorio

    Returns:
        Tuple[bool, Optional[str], Optional[Recordatorio]]: 
            - Éxito de la operación
            - Mensaje de error (si hay)
            - Objeto Recordatorio creado (si fue exitoso)
    """
    try:
        logger.info(f"Iniciando inserción de recordatorio para {datos.get('nombre')}")

        # Verificar que el usuario está autenticado
        if not current_user or not current_user.is_authenticated:
            return False, "Usuario no autenticado", None

        # Validar datos requeridos
        campos_requeridos = ['nombre', 'telefono', 'fecha', 'hora', 'mensaje']
        for campo in campos_requeridos:
            if campo not in datos:
                return False, f"Falta el campo requerido: {campo}", None

        # Crear instancia de Recordatorio
        recordatorio = Recordatorio(
            nombre=datos['nombre'],
            telefono=datos['telefono'],
            fecha=datetime.strptime(datos['fecha'], '%Y-%m-%d').date(),
            hora=datetime.strptime(datos['hora'], '%H:%M').time(),
            mensaje=datos['mensaje'],
            tipo=datos.get('tipo', 'llamada'),
            repeticion=datos.get('repeticion', 'ninguna'),
            user_id=current_user.id  # Asignar el ID del usuario actual
        )

        # Guardar en la base de datos
        db.session.add(recordatorio)
        db.session.commit()

        logger.info(f"Recordatorio creado exitosamente con ID {recordatorio.id} para usuario {current_user.id}")
        return True, None, recordatorio

    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos: {str(e)}")
        db.session.rollback()
        return False, f"Error al guardar en la base de datos: {str(e)}", None

    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        db.session.rollback()
        return False, f"Error inesperado: {str(e)}", None
