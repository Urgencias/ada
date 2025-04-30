import os
import requests
import logging
import json
from datetime import datetime
from models import RegistroLlamada, Recordatorio, User, db

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_netelip_connection():
    """
    Script de prueba para verificar la conexión con Netelip y visibilidad del número
    """
    try:
        # Credenciales y configuración
        token = os.environ.get('NETELIP_TOKEN')
        api_id = os.environ.get('NETELIP_API_ID')
        origen = os.environ.get('ORIGEN_LLAMADA', '968972418')

        logger.info("=== Prueba de Conexión y Visibilidad de Número ===")
        logger.info(f"Número de origen a usar: {origen}")
        logger.info("Verificando que el número comience con 968 (visible)")

        if not origen.startswith('968'):
            logger.error("ERROR CRÍTICO: El número no tiene el formato correcto para ser visible")
            return False, "El número debe comenzar con 968 para ser visible", None

        # URL base y endpoint
        base_url = "https://api.netelip.com/v1/voice"

        # Datos de prueba
        data = {
            'token': token,
            'api': api_id,
            'src': origen,
            'dst': '0034968972418',  # Número de prueba
            'duration': '5',
            'text': 'Esta es una prueba de visibilidad del número',
            'tts': '1',
            'voice': 'Silvia',
            'format': 'json'
        }

        # Verificación de seguridad
        if 'hide_number' in data or 'hide' in data:
            logger.error("¡ALERTA! Detectado intento de ocultar número")
            return False, "No se permite ocultar el número", None

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        logger.info("Enviando solicitud de prueba...")
        response = requests.post(
            base_url,
            data=data,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            try:
                respuesta = response.json()
                logger.info(f"Respuesta: {json.dumps(respuesta, indent=2)}")
                return True, "Prueba exitosa - Número visible confirmado", respuesta
            except json.JSONDecodeError as e:
                return False, f"Error decodificando respuesta: {str(e)}", None
        else:
            return False, f"Error {response.status_code}: {response.text}", None

    except Exception as e:
        logger.error(f"Error en prueba: {str(e)}")
        return False, str(e), None

def realizar_llamada_prueba(mensaje: str = "Esta es una llamada de prueba. Por favor confirme si ve el número 968 correctamente."):
    """Realiza una llamada de prueba usando Netelip con número visible"""
    from utils.netelip import realizar_llamada

    try:
        numero_destino = "0034968972418"  # Número de prueba
        logger.info(f"=== Iniciando llamada de prueba con número visible ===")
        logger.info(f"Número destino: {numero_destino}")

        exito, id_llamada, error = realizar_llamada(
            numero_destino=numero_destino,
            mensaje=mensaje,
            duracion=15
        )

        if exito:
            logger.info(f"Llamada de prueba exitosa (número visible). ID: {id_llamada}")
            return True, id_llamada
        logger.error(f"Error en llamada de prueba: {error}")
        return False, error

    except Exception as e:
        logger.error(f"Error en llamada de prueba: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Prueba completa del sistema
    print("\n=== Iniciando pruebas del sistema de llamadas ===")

    # 1. Probar conexión y visibilidad del número
    success, message, response = test_netelip_connection()
    print(f"\nPrueba de conexión y visibilidad:")
    print(f"{'ÉXITO' if success else 'ERROR'}: {message}")
    if response:
        print(f"Respuesta detallada: {json.dumps(response, indent=2)}")

    # 2. Realizar llamada de prueba
    print("\nRealizando llamada de prueba con número visible...")
    resultado, mensaje = realizar_llamada_prueba()
    print(f"Resultado: {'ÉXITO' if resultado else 'ERROR'}")
    print(f"Mensaje: {mensaje}")