"""Sistema de llamadas automatizadas con soporte para múltiples proveedores y líneas"""
import os
import logging
import time
from datetime import datetime, timedelta
from models import RegistroLlamada
from extensions import db
from utils.netelip import realizar_llamada as realizar_llamada_netelip, verificar_credenciales as verificar_netelip

# Configurar logging específico para proveedores de llamadas
logger = logging.getLogger(__name__)

class GestorProveedores:
    """Gestiona los proveedores de llamadas (Netelip) con soporte para múltiples líneas"""

    MAX_INTENTOS = 3  # Reducido para evitar bloqueos
    TIEMPO_ESPERA = 5  # Reducido a 5 segundos entre intentos
    TIEMPO_MAXIMO_BLOQUEO = 30  # Reducido a 30 segundos máximo
    MIN_DURACION_LLAMADA = 15  # Duración establecida a 15 segundos exactos

    def __init__(self):
        self.netelip_token = os.environ.get('NETELIP_TOKEN')
        self.netelip_api_id = os.environ.get('NETELIP_API_ID')
        # Lista de números de origen disponibles (asegurando formato 34XXXXXXXXX)
        numeros_raw = [
            os.environ.get('ORIGEN_LLAMADA', '968972418'),
            os.environ.get('ORIGEN_LLAMADA_2', '968972419'),
            os.environ.get('ORIGEN_LLAMADA_3', '968972420')
        ]
        # Formatear números al inicializar
        self.numeros_origen = [
            f"34{num.lstrip('0').lstrip('34')}" for num in numeros_raw
        ]
        self.indice_numero_actual = 0
        self.ultima_llamada = datetime.now() - timedelta(seconds=10)
        self.intentos_consecutivos = 0

        logger.info("=== Inicialización del Gestor de Proveedores ===")
        logger.info(f"Configuración:")
        logger.info(f"- Máximo intentos: {self.MAX_INTENTOS}")
        logger.info(f"- Tiempo entre reintentos: {self.TIEMPO_ESPERA}s")
        logger.info(f"- Duración mínima llamada: {self.MIN_DURACION_LLAMADA}s")
        logger.info(f"- Números de origen disponibles: {self.numeros_origen}")

    def _obtener_siguiente_numero(self):
        """Obtiene el siguiente número de origen disponible de forma rotativa"""
        numero = self.numeros_origen[self.indice_numero_actual]
        self.indice_numero_actual = (self.indice_numero_actual + 1) % len(self.numeros_origen)
        logger.info(f"Número de origen seleccionado: {numero}")
        return numero

    def _esperar_rate_limit(self):
        """Gestiona el límite de velocidad de las llamadas"""
        tiempo_desde_ultima = (datetime.now() - self.ultima_llamada).total_seconds()
        if tiempo_desde_ultima < 5:  # Reducido a 5 segundos entre llamadas
            tiempo_espera = 5 - tiempo_desde_ultima
            logger.info(f"Esperando {tiempo_espera:.1f} segundos para respetar el límite de velocidad")
            time.sleep(tiempo_espera)
        self.ultima_llamada = datetime.now()

    def realizar_llamada(self, registro_llamada: RegistroLlamada) -> bool:
        """Realiza una llamada usando Netelip con configuración en español y múltiples líneas"""
        try:
            logger.info(f"=== Iniciando llamada {registro_llamada.id} ===")

            # Validar número de teléfono
            telefono = registro_llamada.recordatorio.telefono
            if not telefono:
                logger.error("Número de teléfono inválido")
                return False

            # Obtener siguiente número de origen (ya formateado como 34XXXXXXXXX)
            numero_origen = self._obtener_siguiente_numero()
            logger.info(f"Usando número de origen: {numero_origen}")
            logger.info(f"Número destino: {telefono}")

            # Realizar la llamada con Netelip
            exito, id_llamada, error = realizar_llamada_netelip(
                telefono,
                registro_llamada.recordatorio.mensaje,
                duracion=self.MIN_DURACION_LLAMADA,
                numero_origen=numero_origen
            )

            if exito and id_llamada:
                registro_llamada.id_llamada_netelip = id_llamada
                registro_llamada.proveedor = 'netelip'
                registro_llamada.estado = 'iniciada'
                registro_llamada.fecha_actualizacion = datetime.now()
                registro_llamada.numero_origen = numero_origen  # Guardamos el número usado
                db.session.commit()
                logger.info(f"Llamada {registro_llamada.id} iniciada exitosamente desde {numero_origen}")
                self.intentos_consecutivos = 0
                return True

            # Control de errores específicos
            if error and '429' in str(error):
                logger.warning(f"Detectado límite de velocidad (429) en línea {numero_origen}, aumentando tiempo de espera")
                self.intentos_consecutivos += 1
                tiempo_espera = min(10 * (2 ** self.intentos_consecutivos), self.TIEMPO_MAXIMO_BLOQUEO)
                time.sleep(tiempo_espera)
            else:
                logger.error(f"Error en llamada {registro_llamada.id} desde {numero_origen}: {error}")
                registro_llamada.estado = 'error'
                registro_llamada.notas = f"Error (línea {numero_origen}): {error}"
                registro_llamada.fecha_actualizacion = datetime.now()
                db.session.commit()

            return False

        except Exception as e:
            logger.error(f"Error inesperado en llamada {registro_llamada.id}: {str(e)}")
            logger.exception("Stacktrace completo:")
            registro_llamada.estado = 'error'
            registro_llamada.notas = str(e)
            registro_llamada.fecha_actualizacion = datetime.now()
            db.session.commit()
            return False

    def procesar_llamadas_pendientes(self):
        """Procesa todas las llamadas pendientes que deberían haberse ejecutado"""
        try:
            ahora = datetime.now()
            logger.info("=== Buscando llamadas pendientes ===")

            # Buscar todas las llamadas pendientes que deberían haberse ejecutado
            llamadas_pendientes = (RegistroLlamada.query
                .join(RegistroLlamada.recordatorio)
                .filter(
                    RegistroLlamada.estado.in_(['pendiente', 'programada']),
                    RegistroLlamada.intentos < self.MAX_INTENTOS
                )
                .all())

            if llamadas_pendientes:
                logger.info(f"Encontradas {len(llamadas_pendientes)} llamadas para procesar")
                for llamada in llamadas_pendientes:
                    try:
                        fecha_hora_llamada = datetime.combine(
                            llamada.recordatorio.fecha,
                            llamada.recordatorio.hora
                        )

                        # Solo procesar si la hora programada ya pasó
                        if fecha_hora_llamada <= ahora:
                            logger.info(f"Procesando llamada {llamada.id} programada para {fecha_hora_llamada} (intento {llamada.intentos + 1})")
                            exito = self.realizar_llamada(llamada)

                            if not exito:
                                llamada.intentos += 1
                                if llamada.intentos >= self.MAX_INTENTOS:
                                    llamada.estado = 'error'
                                    llamada.notas = 'Máximo de intentos alcanzado'
                                else:
                                    llamada.estado = 'pendiente'
                                    llamada.siguiente_intento = ahora + timedelta(seconds=5)  # Reducido a 5 segundos
                                db.session.commit()
                        else:
                            logger.debug(f"Llamada {llamada.id} programada para {fecha_hora_llamada} aún no debe ejecutarse")

                    except Exception as e:
                        logger.error(f"Error procesando llamada {llamada.id}: {str(e)}")
                        continue

            else:
                logger.debug("No hay llamadas pendientes para procesar en este momento")

        except Exception as e:
            logger.error(f"Error en procesamiento de llamadas: {str(e)}")
            logger.exception("Stacktrace completo:")

    def verificar_estado_netelip(self):
        """Verifica el estado de la conexión con Netelip"""
        try:
            exito, mensaje = verificar_netelip()
            return {
                'estado': 'activo' if exito else 'error',
                'mensaje': mensaje,
                'lineas_disponibles': len(self.numeros_origen)
            }
        except Exception as e:
            logger.error(f"Error verificando estado de Netelip: {str(e)}")
            return {
                'estado': 'error',
                'mensaje': str(e)
            }

# Instancia global del gestor de proveedores
gestor_proveedores = GestorProveedores()