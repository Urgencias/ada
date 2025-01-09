# Contenido del archivo utils/test_twilio.py
import os
import logging
from twilio.rest import Client

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_twilio_connection():
    """Script de prueba para verificar la conexión con Twilio"""
    try:
        # Obtener credenciales
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        test_number = os.environ.get('NETELIP_TEST_PHONE', '640523789')

        # Verificar credenciales
        logger.info("=== Credenciales Twilio ===")
        logger.info(f"Account SID presente: {bool(account_sid)}")
        logger.info(f"Auth Token presente: {bool(auth_token)}")
        logger.info(f"Número Twilio presente: {bool(twilio_number)}")
        
        if not all([account_sid, auth_token, twilio_number]):
            return False, "Faltan credenciales de Twilio"

        # Inicializar cliente
        client = Client(account_sid, auth_token)
        
        # Formatear número de prueba
        if not test_number.startswith('+'):
            test_number = f'+34{test_number.lstrip("0034")}'

        # TwiML simple para la prueba
        twiml = '''
        <Response>
            <Say language="es-ES">Esta es una llamada de prueba del sistema.</Say>
        </Response>
        '''

        # Realizar llamada de prueba
        logger.info(f"Intentando llamada de prueba a {test_number}")
        call = client.calls.create(
            twiml=twiml,
            to=test_number,
            from_=twilio_number
        )

        logger.info(f"Llamada iniciada con SID: {call.sid}")
        return True, f"Llamada de prueba iniciada. SID: {call.sid}"

    except Exception as e:
        error_msg = f"Error en prueba Twilio: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

if __name__ == "__main__":
    success, message = test_twilio_connection()
    print(f"Resultado: {'Éxito' if success else 'Error'}")
    print(f"Mensaje: {message}")
