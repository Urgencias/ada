import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models import Recordatorio, RegistroLlamada, User, EstadoLlamadaEnum
from extensions import db
from utils.call_providers import gestor_proveedores
from sqlalchemy import and_

logger = logging.getLogger(__name__)
panel_logger = logging.getLogger('panel_control')
panel_logger.setLevel(logging.DEBUG)

class PanelControl:
    """Gestiona las operaciones centrales del panel de control"""

    LIMITE_LLAMADAS_GRATUITAS = 100

    @staticmethod
    def es_usuario_gratuito(user_id: int) -> bool:
        """Determina si un usuario es gratuito"""
        try:
            usuario = User.query.get(user_id)
            return usuario and not usuario.es_admin
        except Exception as e:
            logger.error(f"Error al verificar tipo de usuario {user_id}: {str(e)}")
            return True  # Por defecto, tratar como gratuito por seguridad

    @staticmethod
    def obtener_limite_llamadas(user_id: int) -> Dict:
        """Obtiene la información de límites para un usuario"""
        try:
            usuario = User.query.get(user_id)
            if not usuario:
                return {}

            # Si es admin, no tiene límites
            if usuario.es_admin:
                return {
                    'es_gratuito': False,
                    'limite_llamadas': None,
                    'llamadas_disponibles': None,
                    'llamadas_realizadas': None
                }

            # Usuario gratuito
            return {
                'es_gratuito': True,
                'limite_llamadas': PanelControl.LIMITE_LLAMADAS_GRATUITAS,
                'llamadas_disponibles': usuario.llamadas_disponibles,
                'llamadas_realizadas': usuario.llamadas_realizadas
            }
        except Exception as e:
            logger.error(f"Error al obtener límites para usuario {user_id}: {str(e)}")
            return {}

    @staticmethod
    def obtener_contadores(user_id: Optional[int] = None) -> Dict:
        """Obtiene los contadores del sistema filtrados por usuario si se especifica"""
        try:
            # Consulta base
            query = RegistroLlamada.query

            # Si hay user_id, filtrar por usuario
            if user_id:
                query = query.join(
                    Recordatorio,
                    RegistroLlamada.recordatorio_id == Recordatorio.id
                ).filter(Recordatorio.user_id == user_id)

            # Contadores básicos para todos los usuarios
            contadores = {
                'total_llamadas': query.count(),
                'llamadas_completadas': query.filter_by(estado=EstadoLlamadaEnum.COMPLETADA).count(),
                'llamadas_pendientes': query.filter(
                    RegistroLlamada.estado.in_([EstadoLlamadaEnum.PENDIENTE, EstadoLlamadaEnum.PROGRAMADA])
                ).count(),
                'llamadas_en_curso': query.filter_by(estado=EstadoLlamadaEnum.EN_CURSO).count(),
                'llamadas_fallidas': query.filter(
                    RegistroLlamada.estado.in_([EstadoLlamadaEnum.FALLIDA, EstadoLlamadaEnum.FALLIDA_PERMANENTE])
                ).count()
            }

            # Agregar información de límites solo para usuarios específicos
            if user_id:
                info_limites = PanelControl.obtener_limite_llamadas(user_id)
                contadores.update(info_limites)

            return contadores

        except Exception as e:
            logger.error(f"Error al obtener contadores: {str(e)}")
            return {
                'total_llamadas': 0,
                'llamadas_completadas': 0,
                'llamadas_pendientes': 0,
                'llamadas_en_curso': 0,
                'llamadas_fallidas': 0
            }

    @staticmethod
    def verificar_limite_llamadas(user_id: int) -> Tuple[bool, str]:
        """Verifica si un usuario puede realizar más llamadas"""
        try:
            if not PanelControl.es_usuario_gratuito(user_id):
                return True, "Usuario premium - sin límite de llamadas"

            info = PanelControl.obtener_limite_llamadas(user_id)
            llamadas_disponibles = info.get('llamadas_disponibles', 0)
            llamadas_realizadas = info.get('llamadas_realizadas', 0)

            if llamadas_realizadas >= llamadas_disponibles:
                return False, f"Has alcanzado el límite de {PanelControl.LIMITE_LLAMADAS_GRATUITAS} llamadas"

            return True, f"Tienes {llamadas_disponibles - llamadas_realizadas} llamadas disponibles"

        except Exception as e:
            logger.error(f"Error al verificar límites: {str(e)}")
            return False, "Error al verificar límites"

    @staticmethod
    def obtener_llamadas_recientes(user_id: Optional[int] = None, limite: int = 50) -> List[RegistroLlamada]:
        """Obtiene las llamadas más recientes filtradas por usuario si se especifica"""
        try:
            query = RegistroLlamada.query

            if user_id:
                query = query.join(
                    Recordatorio,
                    RegistroLlamada.recordatorio_id == Recordatorio.id
                ).filter(Recordatorio.user_id == user_id)

            return query.order_by(RegistroLlamada.fecha_llamada.desc()).limit(limite).all()
        except Exception as e:
            logger.error(f"Error al obtener llamadas recientes: {str(e)}")
            return []

    @staticmethod
    def obtener_estado_sistema() -> Dict:
        """Obtiene el estado actual del sistema incluyendo proveedores"""
        try:
            estado = {
                'estado': 'operativo',
                'ultima_actualizacion': datetime.now().isoformat(),
                'proveedores': {}
            }

            try:
                estado['proveedores'] = gestor_proveedores.obtener_estado()
            except Exception as e:
                logger.error(f"Error al obtener estado de proveedores: {str(e)}")
                estado['proveedores'] = {
                    'estado': 'error',
                    'mensaje': str(e)
                }

            return estado
        except Exception as e:
            logger.error(f"Error al obtener estado del sistema: {str(e)}")
            return {
                'estado': 'error',
                'mensaje': str(e),
                'ultima_actualizacion': datetime.now().isoformat()
            }

    @staticmethod
    def procesar_reintentos() -> None:
        """Procesa las llamadas pendientes de reintento"""
        try:
            # Obtener llamadas que requieren reintento
            llamadas_reintento = RegistroLlamada.query.filter(
                and_(
                    RegistroLlamada.estado == EstadoLlamadaEnum.PENDIENTE,
                    RegistroLlamada.intentos > 0,
                    RegistroLlamada.siguiente_intento <= datetime.now()
                )
            ).all()

            panel_logger.info(f"Procesando {len(llamadas_reintento)} llamadas pendientes de reintento")

            for registro in llamadas_reintento:
                try:
                    if registro.intentos >= gestor_proveedores.MAX_INTENTOS:
                        registro.estado = EstadoLlamadaEnum.FALLIDA_PERMANENTE
                        registro.error_mensaje = f'Máximo de intentos alcanzado ({gestor_proveedores.MAX_INTENTOS})'
                        db.session.commit()
                        panel_logger.warning(f"Llamada {registro.id} marcada como fallida permanente por máximo de intentos")
                        continue

                    panel_logger.info(f"Reintentando llamada {registro.id} (Intento {registro.intentos + 1}/{gestor_proveedores.MAX_INTENTOS})")

                    resultado = gestor_proveedores.realizar_llamada(registro)
                    if resultado:
                        registro.estado = EstadoLlamadaEnum.INICIADA
                        panel_logger.info(f"Reintento exitoso para llamada {registro.id}")
                    else:
                        registro.estado = EstadoLlamadaEnum.PENDIENTE
                        registro.siguiente_intento = datetime.now() + timedelta(seconds=gestor_proveedores.TIEMPO_ESPERA)
                        panel_logger.warning(f"Reintento fallido para llamada {registro.id}")

                    db.session.commit()

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
            # Obtener llamadas iniciadas o en curso en las últimas 24 horas
            llamadas_recientes = RegistroLlamada.query.filter(
                RegistroLlamada.fecha_llamada >= datetime.now() - timedelta(hours=24),
                RegistroLlamada.estado.in_([EstadoLlamadaEnum.INICIADA, EstadoLlamadaEnum.EN_CURSO])
            ).all()

            panel_logger.info(f"Verificando {len(llamadas_recientes)} llamadas recientes")

            for registro in llamadas_recientes:
                try:
                    panel_logger.info(f"Verificando llamada ID: {registro.id}, Estado actual: {registro.estado}")

                    # Verificar estado con el proveedor correspondiente
                    estado = None
                    if registro.proveedor == 'netelip':
                        estado = gestor_proveedores.verificar_estado_netelip(registro)
                    elif registro.proveedor == 'twilio':
                        estado = gestor_proveedores.verificar_estado_twilio(registro)
                    else:
                        panel_logger.error(f"Proveedor desconocido para llamada {registro.id}: {registro.proveedor}")
                        continue

                    if estado['estado'] == EstadoLlamadaEnum.COMPLETADA:
                        registro.estado = EstadoLlamadaEnum.COMPLETADA
                        registro.error_mensaje = None
                        panel_logger.info(f"Llamada {registro.id} completada exitosamente")
                    elif estado['estado'] in [EstadoLlamadaEnum.FALLIDA, EstadoLlamadaEnum.ERROR]:
                        if registro.intentos < gestor_proveedores.MAX_INTENTOS:
                            registro.estado = EstadoLlamadaEnum.PENDIENTE
                            registro.siguiente_intento = datetime.now() + timedelta(seconds=gestor_proveedores.TIEMPO_ESPERA)
                            panel_logger.warning(f"Llamada {registro.id} programada para reintento")
                        else:
                            registro.estado = EstadoLlamadaEnum.FALLIDA_PERMANENTE
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
            fecha_fin: Optional[datetime] = None) -> List[Recordatorio]:
        """Busca recordatorios según criterios especificados"""
        try:
            query = Recordatorio.query

            if termino:
                query = query.filter(
                    (Recordatorio.nombre.ilike(f"%{termino}%"))
                    | (Recordatorio.mensaje.ilike(f"%{termino}%")))

            if tipo:
                query = query.filter_by(tipo=tipo)

            if fecha_inicio:
                query = query.filter(Recordatorio.fecha >= fecha_inicio)

            if fecha_fin:
                query = query.filter(Recordatorio.fecha <= fecha_fin)

            resultados = query.order_by(Recordatorio.fecha.desc()).all()
            panel_logger.info(
                f"Búsqueda completada: {len(resultados)} recordatorios encontrados"
            )
            return resultados

        except Exception as e:
            panel_logger.error(f"Error en búsqueda de recordatorios: {str(e)}")
            return []