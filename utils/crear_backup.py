from utils.backup_system import BackupSystem
import logging

logger = logging.getLogger(__name__)

def crear_respaldo():
    """Crear un nuevo respaldo del sistema"""
    try:
        exito, ruta_backup = BackupSystem.create_backup()
        if exito:
            return True, f"Respaldo creado exitosamente en: {ruta_backup}"
        return False, f"Error al crear el respaldo: {ruta_backup}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

if __name__ == "__main__":
    exito, mensaje = crear_respaldo()
    print(mensaje)
