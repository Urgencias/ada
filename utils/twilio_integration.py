import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def realizar_llamada_twilio(numero_destino: str, mensaje: str, duracion: int = 15) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Realiza una llamada usando la API de Twilio asegurando que se muestre el número de origen

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
        logger.info(f"Número que se mostrará: {twilio_number}")

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

        # Realizar la llamada con configuración explícita del número saliente
        call = client.calls.create(
            twiml=twiml,
            to=numero_destino,
            from_=twilio_number,
            caller_id=twilio_number,  # Asegurar que se muestre el número
            timeout=max(30, duracion + 15),
            status_callback=os.environ.get('TWILIO_STATUS_CALLBACK_URL'),
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
            machine_detection='Enable'
        )

        logger.info(f"Llamada creada con SID: {call.sid}")
        logger.info(f"Número configurado para mostrarse: {twilio_number}")
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

def verificar_estado_llamada(call_sid: str) -> Dict[str, Any]:
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
                'mensaje': 'Faltan credenciales de Twilio'
            }

        # Inicializar cliente
        client = Client(account_sid, auth_token)

        # Obtener estado de la llamada
        call = client.calls(call_sid).fetch()

        # Mapear estados de Twilio a estados internos
        estado_mapping = {
            'completed': 'completada',
            'failed': 'fallida',
            'no-answer': 'sin_respuesta',
            'busy': 'ocupado',
            'in-progress': 'en_curso'
        }

        return {
            'estado': estado_mapping.get(call.status, 'desconocido'),
            'duracion': int(call.duration or 0),
            'ultima_actualizacion': datetime.now().isoformat()
        }

    except TwilioRestException as e:
        logger.error(f"Error Twilio verificando llamada {call_sid}: {e.msg}")
        return {
            'estado': 'error',
            'mensaje': f"Error de Twilio: {e.msg}"
        }

    except Exception as e:
        logger.error(f"Error inesperado verificando llamada {call_sid}: {str(e)}")
        return {
            'estado': 'error',
            'mensaje': f"Error inesperado: {str(e)}"
        }

def procesar_callback_twilio(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa los callbacks de estado de Twilio

    Args:
        data: Datos del callback de Twilio

    Returns:
        dict con la información procesada
    """
    try:
        return {
            'call_sid': data.get('CallSid'),
            'estado': data.get('CallStatus'),
            'duracion': int(data.get('CallDuration', 0)),
            'timestamp': datetime.now(),
            'detalles': {
                'answered_by': data.get('AnsweredBy'),
                'direction': data.get('Direction'),
                'from': data.get('From'),
                'to': data.get('To'),
                'error_code': data.get('ErrorCode'),
                'error_message': data.get('ErrorMessage')
            }
        }
    except Exception as e:
        logger.error(f"Error procesando callback de Twilio: {str(e)}")
        return {
            'estado': 'error',
            'mensaje': f"Error procesando callback: {str(e)}"
        }

# Exportar las funciones necesarias
__all__ = ['realizar_llamada_twilio', 'verificar_estado_llamada', 'procesar_callback_twilio']