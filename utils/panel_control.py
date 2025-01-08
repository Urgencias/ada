import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import Recordatorio, RegistroLlamada
from extensions import db
from utils.call_providers import gestor_proveedores

logger = logging.getLogger(__name__)
panel_logger = logging.getLogger('panel_control')
panel_logger.setLevel(logging.DEBUG)

class PanelControl:
    """Gestiona las operaciones centrales del panel de control"""

    @staticmethod
    def obtener_estadisticas() -> Dict:
        """Obtiene estadísticas generales del sistema"""
        try:
            hoy = datetime.now().date()
            semana_siguiente = hoy + timedelta(days=7)

            # Obtener llamadas pendientes de reintento
            llamadas_reintento = RegistroLlamada.query.filter_by(
                estado='pendiente_reintento'
            ).filter(
                RegistroLlamada.siguiente_intento <= datetime.now()
            ).count()

            stats = {
                'total_recordatorios': Recordatorio.query.count(),
                'recordatorios_hoy': Recordatorio.query.filter_by(fecha=hoy).count(),
                'proximos_7_dias': Recordatorio.query.filter(
                    Recordatorio.fecha >= hoy,
                    Recordatorio.fecha <= semana_siguiente
                ).count(),
                'llamadas_exitosas': RegistroLlamada.query.filter_by(estado='completada').count(),
                'llamadas_fallidas': RegistroLlamada.query.filter_by(estado='fallida_permanente').count(),
                'llamadas_pendientes': RegistroLlamada.query.filter_by(estado='pendiente').count(),
                'llamadas_reintento': llamadas_reintento,
                'proveedores': {
                    'netelip': gestor_proveedores.verificar_estado_netelip(),
                    'twilio': gestor_proveedores.verificar_estado_twilio()
                }
            }

            panel_logger.info(f"Estadísticas generadas exitosamente: {stats}")
            return stats

        except Exception as e:
            panel_logger.error(f"Error al obtener estadísticas: {str(e)}")
            panel_logger.exception("Stacktrace completo:")
            return {}

    @staticmethod
    def procesar_reintentos() -> None:
        """Procesa las llamadas pendientes de reintento"""
        try:
            # Obtener llamadas que necesitan reintento
            llamadas_reintento = RegistroLlamada.query.filter_by(
                estado='pendiente_reintento'
            ).filter(
                RegistroLlamada.siguiente_intento <= datetime.now()
            ).all()

            panel_logger.info(f"Procesando {len(llamadas_reintento)} llamadas pendientes de reintento")

            for registro in llamadas_reintento:
                try:
                    if registro.intentos >= gestor_proveedores.MAX_INTENTOS:
                        registro.estado = 'fallida_permanente'
                        registro.notas = f'Máximo de intentos alcanzado ({gestor_proveedores.MAX_INTENTOS})'
                        db.session.commit()
                        panel_logger.warning(f"Llamada {registro.id} marcada como fallida permanente por máximo de intentos")
                        continue

                    panel_logger.info(f"Reintentando llamada {registro.id} (Intento {registro.intentos + 1}/{gestor_proveedores.MAX_INTENTOS})")

                    # Intentar la llamada nuevamente
                    resultado = gestor_proveedores.realizar_llamada(registro)

                    if resultado:
                        panel_logger.info(f"Reintento exitoso para llamada {registro.id}")
                    else:
                        panel_logger.warning(f"Reintento fallido para llamada {registro.id}")

                except Exception as e:
                    panel_logger.error(f"Error procesando reintento para llamada {registro.id}: {str(e)}")
                    panel_logger.exception("Stacktrace completo:")
                    continue

        except Exception as e:
            panel_logger.error(f"Error procesando reintentos: {str(e)}")
            panel_logger.exception("Stacktrace completo:")

    @staticmethod
    def verificar_llamadas_recientes() -> None:
        """Verifica el estado de las llamadas recientes y actualiza la base de datos"""
        try:
            # Obtener llamadas recientes (últimas 24 horas)
            llamadas_recientes = RegistroLlamada.query.filter(
                RegistroLlamada.fecha_llamada >= datetime.now() - timedelta(hours=24),
                RegistroLlamada.estado.in_(['iniciada', 'en_progreso'])
            ).all()

            panel_logger.info(f"Verificando {len(llamadas_recientes)} llamadas recientes")

            for registro in llamadas_recientes:
                try:
                    panel_logger.info(f"Verificando llamada ID: {registro.id}, Estado actual: {registro.estado}")

                    if registro.proveedor == 'netelip':
                        estado = gestor_proveedores.verificar_estado_netelip()
                    elif registro.proveedor == 'twilio':
                        estado = gestor_proveedores.verificar_estado_twilio()
                    else:
                        panel_logger.error(f"Proveedor desconocido para llamada {registro.id}: {registro.proveedor}")
                        continue

                    # Actualizar estado según la respuesta
                    if estado['estado'] == 'completada':
                        registro.estado = 'completada'
                        registro.notas = 'Llamada completada exitosamente'
                        panel_logger.info(f"Llamada {registro.id} completada exitosamente")
                    elif estado['estado'] in ['fallida', 'sin_respuesta', 'ocupado']:
                        if registro.intentos < gestor_proveedores.MAX_INTENTOS:
                            registro.estado = 'pendiente_reintento'
                            registro.siguiente_intento = datetime.now() + timedelta(seconds=gestor_proveedores.TIEMPO_ESPERA)
                            panel_logger.warning(f"Llamada {registro.id} programada para reintento")
                        else:
                            registro.estado = 'fallida_permanente'
                            panel_logger.error(f"Llamada {registro.id} marcada como fallida permanente")

                    db.session.commit()

                except Exception as e:
                    panel_logger.error(f"Error verificando llamada {registro.id}: {str(e)}")
                    panel_logger.exception("Stacktrace completo:")
                    continue

        except Exception as e:
            panel_logger.error(f"Error verificando llamadas recientes: {str(e)}")
            panel_logger.exception("Stacktrace completo:")

    @staticmethod
    def buscar_recordatorios(
        termino: str,
        tipo: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[Recordatorio]:
        """Busca recordatorios según criterios especificados"""
        try:
            query = Recordatorio.query

            if termino:
                query = query.filter(
                    (Recordatorio.nombre.ilike(f"%{termino}%")) |
                    (Recordatorio.mensaje.ilike(f"%{termino}%"))
                )

            if tipo:
                query = query.filter_by(tipo=tipo)

            if fecha_inicio:
                query = query.filter(Recordatorio.fecha >= fecha_inicio)

            if fecha_fin:
                query = query.filter(Recordatorio.fecha <= fecha_fin)

            resultados = query.order_by(Recordatorio.fecha.desc()).all()
            panel_logger.info(f"Búsqueda completada: {len(resultados)} recordatorios encontrados")
            return resultados

        except Exception as e:
            panel_logger.error(f"Error en búsqueda de recordatorios: {str(e)}")
            return []