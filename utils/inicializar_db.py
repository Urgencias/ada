import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from extensions import db
from flask_migrate import upgrade

logger = logging.getLogger(__name__)

def inicializar_base_datos(app) -> bool:
    """
    Inicializa la base de datos y crea las tablas necesarias

    Args:
        app: Instancia de Flask

    Returns:
        bool: True si la inicialización fue exitosa
    """
    try:
        logger.info("Iniciando proceso de inicialización de la base de datos...")

        with app.app_context():
            # Verificar conexión a la base de datos
            try:
                db.engine.connect()
                logger.info("Conexión a la base de datos establecida")
            except Exception as e:
                logger.error(f"Error conectando a la base de datos: {str(e)}")
                return False

            # Verificar si las tablas principales existen
            inspector = inspect(db.engine)
            tablas_requeridas = {
                'recordatorios', 'registro_llamadas', 'users', 
                'notificaciones_llamadas', 'numeros_autorizados'
            }

            tablas_existentes = set(inspector.get_table_names())

            # Si no existen todas las tablas, crear el esquema completo
            if not tablas_requeridas.issubset(tablas_existentes):
                logger.info("Creando esquema inicial de la base de datos...")
                try:
                    # Crear todas las tablas
                    db.create_all()
                    logger.info("Esquema inicial creado correctamente")
                except Exception as e:
                    logger.error(f"Error creando esquema inicial: {str(e)}")
                    return False

            # Ejecutar migraciones pendientes
            try:
                upgrade()
                logger.info("Migraciones ejecutadas correctamente")
            except Exception as e:
                logger.error(f"Error ejecutando migraciones: {str(e)}")
                # No retornamos False aquí porque puede que no haya migraciones pendientes

            logger.info("Base de datos inicializada correctamente")
            return True

    except SQLAlchemyError as e:
        logger.error(f"Error de SQLAlchemy al inicializar la base de datos: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error general al inicializar la base de datos: {str(e)}")
        return False

def verificar_esquema() -> bool:
    """
    Verifica que el esquema de la base de datos sea correcto

    Returns:
        bool: True si el esquema es correcto
    """
    try:
        logger.info("Verificando esquema de la base de datos...")

        # Obtener el inspector
        inspector = inspect(db.engine)

        # Verificar existencia de tablas principales
        tablas_requeridas = {
            'users', 'recordatorios', 'registro_llamadas', 
            'notificaciones_llamadas', 'numeros_autorizados'
        }

        tablas_existentes = set(inspector.get_table_names())
        if not tablas_requeridas.issubset(tablas_existentes):
            faltantes = tablas_requeridas - tablas_existentes
            logger.error(f"Faltan las siguientes tablas: {faltantes}")
            return False

        # Verificar columnas de la tabla recordatorios
        columnas_recordatorios = {
            'id', 'nombre', 'telefono', 'fecha', 'hora', 
            'mensaje', 'tipo', 'repeticion', 'creado_en',
            'user_id', 'siguiente_llamada'
        }

        columnas_existentes = {c['name'] for c in inspector.get_columns('recordatorios')}
        if not columnas_recordatorios.issubset(columnas_existentes):
            faltantes = columnas_recordatorios - columnas_existentes
            logger.error(f"Faltan las siguientes columnas en recordatorios: {faltantes}")
            return False

        logger.info("Esquema verificado correctamente")
        return True

    except Exception as e:
        logger.error(f"Error al verificar el esquema: {str(e)}")
        return False