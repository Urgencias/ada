import os
import requests
import logging
from typing import Dict, Optional, Tuple
import json
from datetime import datetime, timedelta
import time
from urllib.parse import urljoin, urlparse
from security import safe_requests

logger = logging.getLogger(__name__)

# Configuración actualizada de Netelip
NETELIP_BASE_URL = 'https://api.netelip.com/v1'
NETELIP_TOKEN = os.environ.get('NETELIP_TOKEN')
NETELIP_API_ID = os.environ.get('NETELIP_API_ID')
ORIGEN_LLAMADA = os.environ.get('ORIGEN_LLAMADA', '968972418')  # Número fijo por defecto
MAX_REINTENTOS = 3
TIEMPO_BASE_REINTENTO = 5  # segundos
MIN_DURACION_LLAMADA = 15  # segundos - duración mínima garantizada

def realizar_llamada(numero_destino: str, mensaje: str, duracion: int = MIN_DURACION_LLAMADA, numero_origen: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Realiza una llamada usando la API de Netelip
    IMPORTANTE: El número de origen SIEMPRE debe ser visible (968972418)
    por tratarse de un servicio social para personas mayores.
    """
    try:
        # Verificar credenciales y parámetros requeridos
        if not all([NETELIP_TOKEN, NETELIP_API_ID]):
            logger.error("Faltan credenciales de Netelip")
            return False, None, "Faltan credenciales de Netelip"

        if not numero_destino or not mensaje:
            logger.error("Número de destino y mensaje son requeridos")
            return False, None, "Número de destino y mensaje son requeridos"

        # SEGURIDAD: Asegurar que siempre se use el número visible del sistema
        origen = numero_origen if numero_origen else ORIGEN_LLAMADA
        if not origen.startswith('968'):
            logger.error("ERROR CRÍTICO: Intento de usar número no visible")
            origen = ORIGEN_LLAMADA  # Forzar número visible del sistema

        # Formatear número de destino (debe ser 0034XXXXXXXXX)
        if not numero_destino:
            logger.error("Número de destino no válido")
            return False, None, "Número de destino no válido"

        numero_destino = numero_destino.replace(" ", "").replace("-", "")
        if not numero_destino.startswith('0034'):
            numero_destino = '0034' + numero_destino.lstrip('34').lstrip('0')

        logger.info(f"=== Iniciando llamada con número visible ===")
        logger.info(f"Número origen (visible): {origen}")
        logger.info(f"Número destino: {numero_destino}")
        logger.info(f"Duración configurada: {duracion} segundos")

        # Configuración de la llamada con número visible
        data = {
            'token': NETELIP_TOKEN,
            'api': NETELIP_API_ID,
            'src': origen,
            'dst': numero_destino,
            'duration': str(duracion),
            'typedst': 'pstn',
            'text': mensaje,
            'tts': '1',
            'voice': 'Silvia',
            'speed': '1.0',
            'format': 'json',
            'wait': '1'     # Esperar 1 segundo antes de empezar
        }

        # SEGURIDAD: Verificar que no haya intentos de ocultar el número
        if 'hide_number' in data or 'hide' in data:
            logger.error("¡ALERTA! Intento de ocultar número detectado y bloqueado")
            data.pop('hide_number', None)
            data.pop('hide', None)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        logger.info("Enviando solicitud a Netelip")
        response = requests.post(url=NETELIP_BASE_URL, data=data, headers=headers, timeout=30)

        logger.debug(f"Respuesta de Netelip - Status: {response.status_code}")
        logger.debug(f"Respuesta completa: {response.text}")

        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('status') == 'ok':
                    call_id = result.get('id')
                    if call_id:
                        logger.info(f"Llamada iniciada exitosamente (número visible). ID: {call_id}")
                        return True, call_id, None

                    logger.error("No se recibió ID de llamada")
                    return False, None, "No se recibió ID de llamada"

                error_msg = result.get('message', 'Error desconocido en la respuesta')
                logger.error(f"Error en la respuesta de Netelip: {error_msg}")
                return False, None, error_msg

            except Exception as e:
                error_msg = f"Error al procesar respuesta: {str(e)}"
                logger.error(error_msg)
                return False, None, error_msg

        error_msg = f"Error HTTP: {response.status_code}"
        logger.error(f"{error_msg}. Respuesta: {response.text}")
        return False, None, error_msg

    except requests.exceptions.Timeout:
        error_msg = "Timeout en la conexión con Netelip"
        logger.error(error_msg)
        return False, None, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Error de conexión con Netelip"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        logger.error(error_msg)
        logger.exception("Stacktrace completo:")
        return False, None, error_msg

def verificar_credenciales() -> Tuple[bool, str]:
    """Verifica si las credenciales de Netelip son válidas"""
    try:
        if not all([NETELIP_TOKEN, NETELIP_API_ID]):
            return False, "Faltan credenciales de Netelip"

        url = f"{NETELIP_BASE_URL}/voice/call"
        params = {
            'token': NETELIP_TOKEN,
            'api': NETELIP_API_ID,
            'format': 'json'
        }

        response = safe_requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            return True, "Credenciales válidas"
        elif response.status_code == 401:
            return False, "Credenciales inválidas"
        else:
            error_msg = f"Error de conexión: {response.status_code}"
            logger.error(f"{error_msg}. Respuesta: {response.text}")
            return False, error_msg

    except Exception as e:
        return False, f"Error verificando credenciales: {str(e)}"
