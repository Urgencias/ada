from utils.backup_system import BackupSystem
import logging

logger = logging.getLogger(__name__)

def restaurar_configuracion(ruta_backup):
    """
    Restaura la configuración del sistema desde un respaldo específico.
    
    Ejemplo de uso:
    python restaurar_backup.py backups/backup_20241226_032518
    """
    try:
        # Intentar restaurar el backup
        exito, mensaje = BackupSystem.restore_backup(ruta_backup)
        
        if exito:
            logger.info(f"Respaldo restaurado exitosamente desde: {ruta_backup}")
            logger.info("Sistema restaurado correctamente")
            return True, "Restauración completada con éxito"
        logger.error(f"Error al restaurar el respaldo: {mensaje}")
        return False, mensaje
    except Exception as e:
        logger.error(f"Error durante la restauración: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python restaurar_backup.py <ruta_del_backup>")
        sys.exit(1)
        
    ruta_backup = sys.argv[1]
    exito, mensaje = restaurar_configuracion(ruta_backup)
    print(mensaje)
