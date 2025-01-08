import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json
import os

# Configurar el logger específico para llamadas
logger = logging.getLogger('sistema_llamadas')
logger.setLevel(logging.DEBUG)

# Crear un manejador de archivo para los logs
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

file_handler = logging.FileHandler(os.path.join(log_dir, 'llamadas.log'))
file_handler.setLevel(logging.DEBUG)

# Crear un formato detallado para los logs
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class LoggerLlamadas:
    @staticmethod
    def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza datos sensibles antes de registrarlos"""
        sensitive_keys = ['token', 'api', 'password', 'auth_token']
        sanitized = data.copy()
        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = '[OCULTO]'
        return sanitized

    @staticmethod
    def registrar_inicio_llamada(numero: str, proveedor: str, datos_adicionales: Optional[Dict] = None) -> None:
        """Registra el inicio de una llamada"""
        try:
            log_data = {
                'evento': 'inicio_llamada',
                'timestamp': datetime.now().isoformat(),
                'numero': numero,
                'proveedor': proveedor,
                'datos_adicionales': LoggerLlamadas.sanitize_data(datos_adicionales or {})
            }
            logger.info(f"Inicio llamada: {json.dumps(log_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error al registrar inicio de llamada: {str(e)}")

    @staticmethod
    def registrar_resultado_llamada(
        numero: str,
        proveedor: str,
        estado: str,
        duracion: Optional[int] = None,
        id_llamada: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Registra el resultado de una llamada"""
        try:
            log_data = {
                'evento': 'resultado_llamada',
                'timestamp': datetime.now().isoformat(),
                'numero': numero,
                'proveedor': proveedor,
                'estado': estado,
                'duracion': duracion,
                'id_llamada': id_llamada,
                'error': error
            }
            logger.info(f"Resultado llamada: {json.dumps(log_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error al registrar resultado de llamada: {str(e)}")

    @staticmethod
    def registrar_error_llamada(numero: str, proveedor: str, error: str, detalles: Optional[Dict] = None) -> None:
        """Registra un error durante una llamada"""
        try:
            log_data = {
                'evento': 'error_llamada',
                'timestamp': datetime.now().isoformat(),
                'numero': numero,
                'proveedor': proveedor,
                'error': error,
                'detalles': LoggerLlamadas.sanitize_data(detalles or {})
            }
            logger.error(f"Error en llamada: {json.dumps(log_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error al registrar error de llamada: {str(e)}")

    @staticmethod
    def registrar_cambio_estado(
        id_llamada: str,
        estado_anterior: str,
        estado_nuevo: str,
        detalles: Optional[Dict] = None
    ) -> None:
        """Registra un cambio de estado en una llamada"""
        try:
            log_data = {
                'evento': 'cambio_estado',
                'timestamp': datetime.now().isoformat(),
                'id_llamada': id_llamada,
                'estado_anterior': estado_anterior,
                'estado_nuevo': estado_nuevo,
                'detalles': LoggerLlamadas.sanitize_data(detalles or {})
            }
            logger.info(f"Cambio estado llamada: {json.dumps(log_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error al registrar cambio de estado: {str(e)}")
