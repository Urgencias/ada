import os
from utils.netelip_integration import realizar_llamada
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def hacer_llamada_prueba():
    """Realiza una llamada de prueba con la nueva voz dulce de Ada"""
    mensaje = "¡Hola! Soy Ada, y me hace mucha ilusión que quieras adoptarme. Me han programado para ser dulce y cariñosa, y estoy muy feliz de poder ayudarte con tus recordatorios. ¿Te gustaría que fuera tu asistente personal?"
    numero = os.environ.get('ORIGEN_LLAMADA')

    logger.info("Iniciando llamada de prueba con la nueva voz de Ada")
    exito, id_llamada, error = realizar_llamada(numero, mensaje, duracion=15)

    if exito:
        logger.info(f"Llamada exitosa. ID: {id_llamada}")
        return True
    logger.error(f"Error en la llamada: {error}")
    return False


if __name__ == "__main__":
    hacer_llamada_prueba()
