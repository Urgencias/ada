"""
Sistema de llamadas automatizadas con soporte para múltiples proveedores
"""
import os
import requests
import logging
import json
from datetime import datetime
from models import RegistroLlamada, Recordatorio, User, db

# Configurar logging detallado para SIP y señalización
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configuración básica de Netelip
NETELIP_BASE_URL = 'https://api.netelip.com/v1/voice'
NETELIP_TOKEN = os.environ.get('NETELIP_TOKEN')
NETELIP_API_ID = os.environ.get('NETELIP_API_ID')
ORIGEN_LLAMADA = os.environ.get('ORIGEN_LLAMADA')  # Número de origen configurado

def realizar_llamada(numero_destino: str, mensaje: str, duracion: int = 15, numero_origen: str = None) -> tuple[bool, str | None, str | None]:
    """
    Realiza una llamada usando la API de Netelip con duración exacta de 15 segundos
    """
    try:
        # Registro detallado del inicio de la llamada
        logger.info(f"=== Iniciando nueva llamada a {datetime.now().isoformat()} ===")
        logger.info(f"Número destino: {numero_destino}")
        logger.info(f"Duración solicitada: {duracion} segundos")
        logger.info(f"Mensaje a reproducir: '{mensaje}'")

        # Verificar credenciales
        if not all([NETELIP_TOKEN, NETELIP_API_ID]):
            logger.error("Faltan credenciales de Netelip")
            return False, None, "Faltan credenciales de Netelip"

        # Validaciones básicas
        if not numero_destino or not mensaje:
            logger.error("Número de destino y mensaje son requeridos")
            return False, None, "Número de destino y mensaje son requeridos"

        # Usar número de origen fijo y formateado
        origen = "34968972418"  # Formato fijo requerido
        logger.info(f"Número de origen configurado: {origen}")

        # Formatear número de destino (debe ser 0034XXXXXXXXX)
        numero_destino = numero_destino.replace(" ", "").replace("-", "").replace("+", "")
        if not numero_destino.startswith('0034'):
            numero_destino = '0034' + numero_destino.lstrip('34').lstrip('0')

        logger.info(f"=== Configuración de la llamada ===")
        logger.info(f"Número origen: {origen}")
        logger.info(f"Número destino formateado: {numero_destino}")
        logger.info(f"Duración objetivo: {duracion} segundos")

        # Configuración optimizada para garantizar duración exacta de 15 segundos
        data = {
            'token': NETELIP_TOKEN,
            'api': NETELIP_API_ID,
            'src': origen,               # Número de origen fijo
            'dst': numero_destino,       # Número destino formateado
            'duration': str(duracion),   # Duración exacta
            'typedst': 'pstn',          # Red telefónica
            'text': mensaje,             # Mensaje TTS
            'tts': '1',                 # Activar TTS
            'voice': 'Silvia',          # Voz en español
            'speed': '0.9',             # Velocidad ajustada para claridad
            'format': 'json',           # Formato respuesta
            'wait': '1',                # Espera mínima
            'show_src': '1',            # Mostrar origen
            'clid': origen,             # Caller ID
            'cli': '1',                 # ID llamada
            'repeat': '0',              # Sin repeticiones
            'repeat_delay': '0',        # Sin delay
            'hangup': '1',              # Colgar auto al finalizar
            'force_duration': '1',      # Forzar duración
            'min_duration': '15',       # Mínimo 15s
            'max_duration': '15',       # Máximo 15s (igual que mínimo)
            'play_beep': '0',           # Sin beep
            'force_hangup': '1',        # Forzar colgar al final
            'silence_threshold': '-1',   # No detectar silencio
            'end_call_on_silence': '0',  # No terminar en silencio
            'timeout': '30',            # Timeout reducido
            'keep_alive': '1',          # Keep-alive
            'allow_early_media': '0',    # No media temprano
            'force_answer': '1',        # Forzar respuesta
            'answer_timeout': '30',      # Timeout respuesta
            'no_answer_timeout': '30',   # Timeout no respuesta
            'busy_timeout': '30',        # Timeout ocupado
            'failed_timeout': '30',      # Timeout error
            'force_connect': '1',        # Forzar conexión
            'retry_on_error': '0',      # No reintentar
            'sip_headers': {            # Headers SIP optimizados
                'X-Custom-Duration': '15',
                'X-Force-Connection': 'true',
                'X-No-Early-Hangup': 'false'
            }
        }

        # Log detallado de la configuración
        logger.info("=== Configuración completa de la llamada ===")
        for key, value in data.items():
            if key in ['token', 'api']:
                logger.info(f"  {key}: {'*' * len(str(value))}")
            else:
                logger.info(f"  {key}: {value}")

        # Headers HTTP optimizados
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=120, max=1000',
            'X-Custom-Call-Duration': '15',
            'X-Force-Keep-Alive': 'true'
        }

        logger.info("=== Enviando solicitud a Netelip ===")
        response = requests.post(
            url=NETELIP_BASE_URL,
            data=data,
            headers=headers,
            timeout=120  # Timeout extendido
        )

        # Procesar respuesta
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Respuesta de Netelip: {json.dumps(result, indent=2)}")

            if result.get('response') == '200' or result.get('status') == 'ok':
                call_id = result.get('ID') or result.get('id')
                if call_id:
                    logger.info(f"=== Llamada iniciada exitosamente ===")
                    logger.info(f"ID llamada: {call_id}")
                    logger.info(f"Duración configurada: {duracion} segundos")
                    return True, call_id, None

                logger.error("No se recibió ID de llamada")
                return False, None, "No se recibió ID de llamada"

            error_msg = result.get('message', 'Error desconocido en la respuesta')
            logger.error(f"Error en respuesta: {error_msg}")
            logger.error(f"Respuesta completa: {json.dumps(result, indent=2)}")
            return False, None, error_msg

        error_msg = f"Error HTTP: {response.status_code}"
        logger.error(f"{error_msg}. Respuesta: {response.text}")
        try:
            error_detail = response.json()
            logger.error(f"Detalles del error: {json.dumps(error_detail, indent=2)}")
        except:
            logger.error("No se pudo parsear la respuesta como JSON")
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

def verificar_credenciales() -> tuple[bool, str]:
    """Verifica si las credenciales de Netelip son válidas"""
    try:
        if not all([NETELIP_TOKEN, NETELIP_API_ID]):
            return False, "Faltan credenciales de Netelip"

        url = NETELIP_BASE_URL
        params = {
            'token': NETELIP_TOKEN,
            'api': NETELIP_API_ID,
            'format': 'json'
        }

        response = requests.get(url, params=params, timeout=30)

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

__all__ = ['realizar_llamada', 'verificar_credenciales']