import threading
import time
import logging
import requests
from datetime import datetime, timedelta
from utils.panel_llamadas import PanelLlamadas
from utils.call_providers import gestor_proveedores
from flask import current_app
from extensions import db
from models import RegistroLlamada, NotificacionLlamada

logger = logging.getLogger(__name__)

def check_missed_calls(app):
    """Función que verifica las llamadas perdidas periódicamente"""
    try:
        logger.info("Iniciando sistema de verificación de llamadas programadas")

        while True:
            try:
                with app.app_context():
                    ahora = datetime.now()

                    # Obtener llamadas que deberían haberse realizado hasta ahora
                    llamadas_pendientes = RegistroLlamada.query.filter(
                        RegistroLlamada.estado.in_(['pendiente', 'programada']),
                        RegistroLlamada.fecha_llamada <= ahora,
                        RegistroLlamada.intentos < 8
                    ).order_by(
                        RegistroLlamada.fecha_llamada
                    ).all()

                    if llamadas_pendientes:
                        logger.info(f"Encontradas {len(llamadas_pendientes)} llamadas pendientes")

                        for llamada in llamadas_pendientes:
                            tiempo_programado = llamada.fecha_llamada
                            retraso = ahora - tiempo_programado

                            logger.info(
                                f"Procesando llamada {llamada.id}:\n"
                                f"  Programada para: {tiempo_programado.strftime('%H:%M:%S')}\n"
                                f"  Retraso actual: {retraso.total_seconds():.1f} segundos\n"
                                f"  Estado: {llamada.estado}\n"
                                f"  Intentos: {llamada.intentos}"
                            )

                            try:
                                # Realizar la llamada inmediatamente
                                exito = gestor_proveedores.realizar_llamada(llamada)

                                if exito:
                                    logger.info(f"Llamada {llamada.id} realizada con éxito")
                                    llamada.estado = 'completada'
                                    llamada.notas = f"Llamada completada (retraso: {retraso.total_seconds():.1f}s)"

                                    # Programar siguiente llamada si es repetitiva
                                    if llamada.recordatorio.repeticion != '0':
                                        siguiente = PanelLlamadas.calcular_siguiente_llamada(llamada.recordatorio)
                                        if siguiente:
                                            nuevo_registro = RegistroLlamada(
                                                recordatorio_id=llamada.recordatorio.id,
                                                fecha_llamada=siguiente,
                                                estado='programada',
                                                intentos=0,
                                                notas='Llamada programada por repetición'
                                            )
                                            db.session.add(nuevo_registro)
                                            logger.info(f"Programada siguiente llamada para {siguiente}")

                                    db.session.commit()
                                else:
                                    logger.warning(f"Falló la llamada {llamada.id}")
                                    llamada.intentos += 1

                                    if llamada.intentos >= 8:
                                        llamada.estado = 'fallida_permanente'
                                        llamada.notas = "Máximo número de intentos alcanzado"
                                    else:
                                        llamada.estado = 'pendiente'
                                        tiempo_espera = 2 * (2 ** (llamada.intentos - 1))  # Backoff exponencial
                                        llamada.siguiente_intento = ahora + timedelta(minutes=tiempo_espera)
                                        llamada.notas = f"Reintento {llamada.intentos} programado en {tiempo_espera} minutos"

                                    db.session.commit()

                            except Exception as e:
                                logger.error(f"Error procesando llamada {llamada.id}: {str(e)}")
                                logger.exception("Stacktrace completo:")
                                continue

                    else:
                        logger.debug("No hay llamadas pendientes en este momento")

            except Exception as e:
                logger.error(f"Error en ciclo de verificación: {str(e)}")
                logger.exception("Stacktrace completo:")
                continue

            # Esperar solo 1 segundo entre verificaciones para mayor precisión
            time.sleep(1)

    except Exception as e:
        logger.error(f"Error fatal en el scheduler: {str(e)}")
        logger.exception("Stacktrace completo:")
        raise

def start_scheduler(app):
    """Inicia el scheduler en un hilo separado"""
    try:
        logger.info("Iniciando scheduler de llamadas programadas")
        scheduler_thread = threading.Thread(target=check_missed_calls, args=(app,), daemon=True)
        scheduler_thread.start()
        return scheduler_thread
    except Exception as e:
        logger.error(f"Error al iniciar scheduler: {str(e)}")
        logger.exception("Stacktrace completo:")
        raise