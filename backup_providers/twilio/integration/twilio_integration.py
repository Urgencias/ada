# Contenido del archivo utils/twilio_integration.py
import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def realizar_llamada_twilio(numero_destino: str, mensaje: str, duracion: int = 15) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Realiza una llamada usando la API de Twilio

    Args:
        numero_destino: Número de teléfono de destino
        mensaje: Mensaje a convertir en voz
        duracion: Duración mínima de la llamada en segundos (default 15s)

    Returns:
        Tuple con (éxito, call_sid, mensaje_error)
    """
    try:
        # Obtener y verificar credenciales
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')

        logger.info("=== Iniciando llamada Twilio ===")
        logger.info(f"Account SID presente: {bool(account_sid)}")
        logger.info(f"Auth Token presente: {bool(auth_token)}")
        logger.info(f"Número Twilio presente: {bool(twilio_number)}")

        if not all([account_sid, auth_token, twilio_number]):
            error_msg = "Faltan credenciales de Twilio"
            logger.error(error_msg)
            return False, None, error_msg

        # Inicializar cliente
        client = Client(account_sid, auth_token)

        # Formatear número de destino
        numero_destino = numero_destino.replace(" ", "").replace("-", "")
        if numero_destino.startswith('0034'):
            numero_destino = '+34' + numero_destino[4:]
        elif not numero_destino.startswith('+34'):
            numero_destino = f'+34{numero_destino}'

        logger.info(f"Número destino formateado: {numero_destino}")
        logger.info(f"Mensaje a enviar: {mensaje}")
        logger.info(f"Duración configurada: {duracion} segundos")

        # TwiML con pausa para asegurar duración mínima y mensaje de fin
        twiml = f'''
        <Response>
            <Say language="es-ES" voice="alice">{mensaje}</Say>
            <Pause length="{max(15, duracion)}"/>
            <Say language="es-ES" voice="alice">Fin del mensaje. Gracias por su atención.</Say>
        </Response>
        '''

        # Realizar la llamada con timeout y callbacks
        call = client.calls.create(
            twiml=twiml,
            to=numero_destino,
            from_=twilio_number,
            timeout=max(30, duracion + 15),  # Asegurar tiempo suficiente
            status_callback=os.environ.get('TWILIO_STATUS_CALLBACK_URL'),
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
            machine_detection='Enable'
        )

        logger.info(f"Llamada creada con SID: {call.sid}")

        # Verificar estado inicial
        call_status = client.calls(call.sid).fetch()
        logger.info(f"Estado inicial de la llamada: {call_status.status}")

        return True, call.sid, None

    except TwilioRestException as e:
        error_msg = f"Error de Twilio: {e.msg}"
        logger.error(f"Código de error Twilio: {e.code}")
        logger.error(f"Mensaje de error Twilio: {e.msg}")
        return False, None, error_msg

    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        logger.error(error_msg)
        logger.exception("Stacktrace completo:")
        return False, None, error_msg

def verificar_estado_llamada_twilio(call_sid: str) -> Dict[str, Any]:
    """
    Verifica el estado de una llamada de Twilio

    Args:
        call_sid: SID de la llamada a verificar

    Returns:
        dict con información del estado de la llamada
    """
    try:
        # Verificar credenciales
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

        if not all([account_sid, auth_token]):
            logger.error("Faltan credenciales de Twilio")
            return {
                'estado': 'error',
                'mensaje': 'Faltan credenciales de Twilio',
                'detalles': None
            }

        # Inicializar cliente
        client = Client(account_sid, auth_token)

        # Obtener estado de la llamada
        call = client.calls(call_sid).fetch()

        return {
            'estado': call.status,
            'duracion': call.duration,
            'inicio': call.start_time,
            'fin': call.end_time,
            'precio': call.price,
            'detalles': {
                'direction': call.direction,
                'answered_by': call.answered_by,
                'caller_name': call.caller_name,
                'queue_time': call.queue_time,
                'machine_detection_result': call.answering_machine_detection,
                'error_code': call.error_code,
                'error_message': call.error_message
            }
        }

    except TwilioRestException as e:
        logger.error(f"Error Twilio verificando llamada {call_sid}: {e.msg}")
        return {
            'estado': 'error',
            'mensaje': f"Error de Twilio: {e.msg}",
            'detalles': None
        }

    except Exception as e:
        logger.error(f"Error inesperado verificando llamada {call_sid}: {str(e)}")
        return {
            'estado': 'error',
            'mensaje': f"Error inesperado: {str(e)}",
            'detalles': None
        }
