import os
import logging
import shutil
from datetime import datetime
import pytz
from utils.timezone_helpers import get_current_time, ZONA_HORARIA_MADRID
import subprocess

logger = logging.getLogger(__name__)

class BackupSystem:
    """Sistema de respaldo automático para la configuración y base de datos"""

    BACKUP_DIR = "backups"
    CONFIG_FILES = [
        'utils/timezone_helpers.py',
        'utils/scheduler.py',
        'utils/panel_llamadas.py',
        'utils/call_providers.py',
        'models.py',
        'routes/main.py'
    ]

    @staticmethod
    def create_backup():
        """Crea un respaldo completo del sistema"""
        try:
            # Crear directorio de respaldo si no existe
            timestamp = get_current_time().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(BackupSystem.BACKUP_DIR, f'backup_{timestamp}')
            os.makedirs(backup_path, exist_ok=True)

            # Respaldar archivos de configuración
            config_backup_path = os.path.join(backup_path, 'config')
            os.makedirs(config_backup_path, exist_ok=True)
            
            for file_path in BackupSystem.CONFIG_FILES:
                if os.path.exists(file_path):
                    # Crear subdirectorios si es necesario
                    dest_path = os.path.join(config_backup_path, file_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Archivo respaldado: {file_path}")

            # Respaldar base de datos usando pg_dump
            db_backup_path = os.path.join(backup_path, 'database.sql')
            db_url = os.environ.get('DATABASE_URL')
            if db_url:
                try:
                    # Usar las variables de entorno existentes para pg_dump
                    result = subprocess.run([
                        'pg_dump',
                        '-F', 'c',  # Formato personalizado
                        '-f', db_backup_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info("Base de datos respaldada exitosamente")
                    else:
                        logger.error(f"Error al respaldar base de datos: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error al ejecutar pg_dump: {str(e)}")

            # Crear archivo de registro
            with open(os.path.join(backup_path, 'backup_info.txt'), 'w') as f:
                f.write(f"Respaldo creado: {get_current_time()}\n")
                f.write("Archivos respaldados:\n")
                for file in BackupSystem.CONFIG_FILES:
                    f.write(f"- {file}\n")

            logger.info(f"Respaldo completo creado en: {backup_path}")
            return True, backup_path

        except Exception as e:
            logger.error(f"Error al crear respaldo: {str(e)}")
            logger.exception("Stacktrace completo:")
            return False, str(e)

    @staticmethod
    def restore_backup(backup_path):
        """Restaura un respaldo específico"""
        try:
            if not os.path.exists(backup_path):
                return False, "Ruta de respaldo no encontrada"

            # Restaurar archivos de configuración
            config_backup_path = os.path.join(backup_path, 'config')
            if os.path.exists(config_backup_path):
                for file_path in BackupSystem.CONFIG_FILES:
                    backup_file = os.path.join(config_backup_path, file_path)
                    if os.path.exists(backup_file):
                        # Crear directorio si no existe
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        shutil.copy2(backup_file, file_path)
                        logger.info(f"Archivo restaurado: {file_path}")

            # Restaurar base de datos
            db_backup_path = os.path.join(backup_path, 'database.sql')
            if os.path.exists(db_backup_path):
                try:
                    result = subprocess.run([
                        'pg_restore',
                        '-d', os.environ.get('DATABASE_URL', ''),
                        '-c',  # Limpiar objetos existentes
                        db_backup_path
                    ], capture_output=True, text=True)

                    
                    if result.returncode == 0:
                        logger.info("Base de datos restaurada exitosamente")
                    else:
                        logger.error(f"Error al restaurar base de datos: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error al ejecutar pg_restore: {str(e)}")
                    return False, f"Error al restaurar base de datos: {str(e)}"

            logger.info(f"Respaldo restaurado desde: {backup_path}")
            return True, "Respaldo restaurado exitosamente"

        except Exception as e:
            logger.error(f"Error al restaurar respaldo: {str(e)}")
            logger.exception("Stacktrace completo:")
            return False, str(e)
