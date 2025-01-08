import os
import logging
import requests
from typing import Optional, Tuple
import re
import time

logger = logging.getLogger(__name__)

def validar_numero(numero: str) -> bool:
    """Valida el formato del número de teléfono"""
    if not numero:
        return False

    # Limpiar el número de espacios y guiones
    numero = numero.strip().replace(" ", "").replace("-", "")

    # Patrones válidos para números españoles:
    # +34XXXXXXXXX
    # 0034XXXXXXXXX
    # 34XXXXXXXXX
    # XXXXXXXXX (9 dígitos)
    patron = r'^(\+34|0034|34)?[6789]\d{8}$'

    # Si el número coincide con el patrón
    if re.match(patron, numero):
        logger.info(f"Número válido: {numero}")
        return True

    logger.warning(f"Número inválido: {numero}")
    return False

def realizar_llamada_simple(
    telefono: str, 
    mensaje: str, 
    voz: str = 'Silvia',
    duracion: int = 60,
    max_intentos: int = 3
) -> Tuple[bool, Optional[str]]:
    """
    Realiza una llamada directa usando Netelip con voz personalizable

    Args:
        telefono: Número de teléfono (formato español)
        mensaje: Mensaje a convertir en voz
        voz: Nombre de la voz a utilizar (default: 'Silvia')
        duracion: Duración mínima de la llamada en segundos (default: 60)
        max_intentos: Número máximo de intentos (default: 3)
    """
    try:
        # Verificar credenciales
        netelip_token = os.environ.get('NETELIP_TOKEN')
        netelip_api_id = os.environ.get('NETELIP_API_ID')
        numero_origen = os.environ.get('ORIGEN_LLAMADA')

        if not all([netelip_token, netelip_api_id, numero_origen]):
            error_msg = "Faltan credenciales de Netelip"
            logger.error(error_msg)
            return False, error_msg

        # Validar número de destino
        if not validar_numero(telefono):
            error_msg = f"Número de teléfono inválido: {telefono}"
            logger.error(error_msg)
            return False, error_msg

        # Formatear número de origen
        if numero_origen:
            origen = numero_origen.strip().replace(" ", "").replace("-", "")
            if origen.startswith('+34'):
                origen = '0034' + origen[3:]
            elif origen.startswith('34'):
                origen = '0034' + origen[2:]
            elif not origen.startswith('0034'):
                origen = '0034' + origen.lstrip('0')

        # Formatear número de destino
        destino = telefono.strip().replace(" ", "").replace("-", "")
        if not destino.startswith('0034'):
            if destino.startswith('+34'):
                destino = '0034' + destino[3:]
            elif destino.startswith('34'):
                destino = '0034' + destino[2:]
            else:
                destino = '0034' + destino.lstrip('0')

        logger.info(f"Iniciando llamada con voz {voz} a {destino}")
        logger.debug(f"Origen formateado: {origen}")
        logger.debug(f"Destino formateado: {destino}")
        logger.debug(f"Duración configurada: {duracion} segundos")

        # URL y datos para la API
        url = 'https://api.netelip.com/v1/voice/call'
        data = {
            'token': netelip_token,
            'api': netelip_api_id,
            'src': origen,
            'dst': destino,
            'text': mensaje,
            'tts': '1',
            'voice': voz,
            'speed': '1.2',
            'duration': str(duracion),
            'response': 'json'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # Sistema de reintentos con backoff exponencial
        for intento in range(max_intentos):
            try:
                logger.info(f"Intento {intento + 1} de {max_intentos}")
                response = requests.post(url, data=data, headers=headers, timeout=duracion + 10)
                logger.debug(f"Código de respuesta: {response.status_code}")
                logger.debug(f"Respuesta: {response.text}")

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'ok':
                        call_id = result.get('id')
                        if call_id:
                            logger.info(f"Llamada iniciada exitosamente. ID: {call_id}")
                            # Esperar la duración mínima configurada
                            time.sleep(duracion)
                            return True, None
                    else:
                        error_msg = result.get('message', 'Error desconocido')
                        logger.error(f"Error en respuesta: {error_msg}")
                        if intento == max_intentos - 1:
                            return False, f"Error de Netelip: {error_msg}"
                else:
                    logger.error(f"Error HTTP: {response.status_code}")
                    if intento == max_intentos - 1:
                        return False, f"Error de conexión: {response.status_code}"

            except requests.exceptions.RequestException as e:
                logger.error(f"Error en solicitud: {str(e)}")
                if intento == max_intentos - 1:
                    return False, f"Error de conexión: {str(e)}"

            # Esperar antes del siguiente intento con backoff exponencial
            if intento < max_intentos - 1:
                time.sleep(2 ** intento)

        return False, "Máximo de intentos alcanzado"

    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        logger.error(error_msg)
        return False, error_msg