import logging
from typing import Dict, Optional
from datetime import datetime
import json
import requests
from flask import current_app

logger = logging.getLogger(__name__)

class ConnectionDiagnostics:
    def __init__(self):
        self.last_check: Dict[str, datetime] = {}
        self.status_cache: Dict[str, Dict] = {}

    @staticmethod
    def check_database_connection() -> Dict:
        """Verifica la conexión a la base de datos"""
        try:
            from extensions import db
            # Realizar una consulta simple para verificar la conexión
            start_time = datetime.now()
            db.session.execute('SELECT 1')
            latency = (datetime.now() - start_time).total_seconds() * 1000

            return {
                'status': 'active',
                'latency': round(latency, 2),
                'last_check': datetime.now().isoformat(),
                'message': 'Conexión a base de datos establecida'
            }
        except Exception as e:
            logger.error(f"Error en conexión a base de datos: {e}")
            return {
                'status': 'error',
                'latency': -1,
                'error': str(e),
                'last_check': datetime.now().isoformat(),
                'message': 'Error en conexión a base de datos'
            }

    @staticmethod
    def check_netelip_connection() -> Dict:
        """Verifica la conexión con Netelip"""
        try:
            # Verificar credenciales de Netelip
            netelip_token = current_app.config.get('NETELIP_TOKEN')
            netelip_api_id = current_app.config.get('NETELIP_API_ID')

            if not netelip_token or not netelip_api_id:
                return {
                    'status': 'warning',
                    'latency': -1,
                    'message': 'Credenciales de Netelip no configuradas',
                    'last_check': datetime.now().isoformat()
                }

            # Hacer una petición de prueba a la API de Netelip
            start_time = datetime.now()
            response = requests.get(
                'https://api.netelip.com/v1/status',
                headers={
                    'X-API-TOKEN': netelip_token,
                    'X-API-ID': netelip_api_id
                },
                timeout=10  # Añadir timeout para evitar bloqueos
            )
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                status = 'active'
                message = 'Conexión con Netelip establecida'
            else:
                status = 'warning'
                message = f'Respuesta inesperada de Netelip: {response.status_code}'

            return {
                'status': status,
                'latency': round(latency, 2),
                'last_check': datetime.now().isoformat(),
                'message': message
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en conexión con Netelip: {e}")
            return {
                'status': 'error',
                'latency': -1,
                'error': str(e),
                'last_check': datetime.now().isoformat(),
                'message': 'Error en conexión con Netelip'
            }

    def check_system_metrics(self) -> Dict:
        """Obtiene métricas del sistema"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            return {
                'cpu': round(cpu_percent, 1),
                'memory': round(memory.percent, 1),
                'connections': len(psutil.net_connections(kind='inet4')),
                'calls_per_minute': self._get_calls_per_minute()
            }
        except Exception as e:
            logger.error(f"Error al obtener métricas del sistema: {e}")
            return {
                'cpu': 0,
                'memory': 0,
                'connections': 0,
                'calls_per_minute': 0
            }

    @staticmethod
    def _get_calls_per_minute() -> int:
        """Obtiene el número de llamadas por minuto"""
        try:
            from models import RegistroLlamada
            from datetime import timedelta

            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)

            # Contar llamadas en el último minuto
            return RegistroLlamada.query.filter(
                RegistroLlamada.fecha_actualizacion >= one_minute_ago
            ).count()
        except Exception as e:
            logger.error(f"Error al obtener llamadas por minuto: {e}")
            return 0

    def get_system_status(self) -> Dict:
        """Obtiene el estado general del sistema"""
        current_time = datetime.now()

        # Verificar todas las conexiones
        status = {
            'timestamp': current_time.isoformat(),
            'database': self.check_database_connection(),
            'api': self.check_netelip_connection(),
            'system': self.check_system_metrics()
        }

        # Determinar estado general
        all_ok = all(
            component.get('status') == 'active'
            for component in [status['database'], status['api']]
        )

        status['overall_status'] = 'active' if all_ok else 'degraded'
        return status

    @staticmethod
    def format_sse_message(data: Dict) -> str:
        """Formatea los datos para Server-Sent Events"""
        return f"data: {json.dumps(data)}\n\n"

# Instancia global para diagnóstico
diagnostics = ConnectionDiagnostics()
