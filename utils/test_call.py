import logging
from datetime import datetime
from utils.call_providers import gestor_proveedores
from models import Recordatorio, RegistroLlamada
from extensions import db

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def realizar_llamada_prueba(numero_destino: str, mensaje: str) -> bool:
    """
    Realiza una llamada de prueba para verificar el sistema
    
    Args:
        numero_destino: Número de teléfono de destino
        mensaje: Mensaje a transmitir
    
    Returns:
        bool: True si la llamada se realizó correctamente, False en caso contrario
    """
    try:
        logger.info(f"Iniciando llamada de prueba a {numero_destino}")
        
        # Crear un recordatorio de prueba
        recordatorio = Recordatorio(
            nombre="Llamada de prueba",
            telefono=numero_destino,
            mensaje=mensaje,
            fecha=datetime.now(),
            tipo="prueba"
        )
        db.session.add(recordatorio)
        db.session.commit()
        logger.info(f"Recordatorio creado con ID: {recordatorio.id}")
        
        # Crear registro de llamada
        registro = RegistroLlamada(
            recordatorio_id=recordatorio.id,
            fecha_llamada=datetime.now(),
            estado='pendiente',
            intentos=0
        )
        db.session.add(registro)
        db.session.commit()
        logger.info(f"Registro de llamada creado con ID: {registro.id}")
        
        # Realizar la llamada
        resultado = gestor_proveedores.realizar_llamada(registro)
        
        if resultado:
            logger.info("Llamada de prueba realizada exitosamente")
            return True
        logger.error("Error al realizar la llamada de prueba")
        return False
    except Exception as e:
        logger.error(f"Error inesperado en llamada de prueba: {str(e)}")
        logger.exception("Stacktrace completo:")
        return False
