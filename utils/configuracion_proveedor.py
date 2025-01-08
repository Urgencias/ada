import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ConfiguracionProveedor:
    def __init__(self):
        """Inicializa la configuración del proveedor de llamadas"""
        # Configuración de llamadas
        self.MAX_INTENTOS = 8  # Número máximo de intentos
        self.INTERVALO_VERIFICACION = 180  # 3 minutos en segundos
        self.DURACION_MINIMA = 15  # Duración mínima en segundos

        # Obtener y formatear la URL base
        api_url = os.environ.get('NETELIP_API_URL', 'https://api.netelip.com/v1')
        if not api_url.startswith(('http://', 'https://')):
            api_url = f'https://{api_url}'
        api_url = api_url.rstrip('/')  # Eliminar trailing slash

        # Obtener y formatear el número de origen
        origen = os.environ.get('ORIGEN_LLAMADA', "968972418")
        # El número de origen debe estar en formato 34XXXXXXXXX (sin 00)
        origen = origen.replace("+", "").replace("00", "").lstrip("34")
        origen = f"34{origen}"

        self.config = {
            'netelip': {
                'api_url': api_url,
                'token': os.environ.get('NETELIP_TOKEN'),
                'api_id': os.environ.get('NETELIP_API_ID'),
                'source': origen,
                'max_intentos': self.MAX_INTENTOS,
                'intervalo_verificacion': self.INTERVALO_VERIFICACION,
                'duracion_minima': self.DURACION_MINIMA
            }
        }

        # Loguear la configuración (ocultando información sensible)
        logger.info("=== Configuración del Proveedor ===")
        logger.info(f"URL base: {api_url}")
        logger.info(f"Token presente: {bool(self.config['netelip']['token'])}")
        logger.info(f"API ID presente: {bool(self.config['netelip']['api_id'])}")
        logger.info(f"Número origen: {self.config['netelip']['source']}")
        logger.info(f"Máximo intentos: {self.MAX_INTENTOS}")
        logger.info(f"Intervalo verificación: {self.INTERVALO_VERIFICACION} segundos")
        logger.info(f"Duración mínima: {self.DURACION_MINIMA} segundos")

    def get_config(self, proveedor: str) -> Optional[Dict]:
        """
        Obtiene la configuración para un proveedor específico

        Args:
            proveedor: Nombre del proveedor (ej: 'netelip')

        Returns:
            Dict con la configuración o None si no existe
        """
        try:
            return self.config.get(proveedor)
        except Exception as e:
            logger.error(f"Error al obtener configuración para {proveedor}: {str(e)}")
            return None

    def validar_configuracion(self, proveedor: str) -> bool:
        """
        Valida que la configuración del proveedor esté completa

        Args:
            proveedor: Nombre del proveedor a validar

        Returns:
            bool: True si la configuración es válida
        """
        try:
            config = self.get_config(proveedor)
            if not config:
                return False

            # Validar campos requeridos
            campos_requeridos = ['api_url', 'token', 'api_id', 'source']
            return all(campo in config and config[campo] for campo in campos_requeridos)

        except Exception as e:
            logger.error(f"Error validando configuración de {proveedor}: {str(e)}")
            return False