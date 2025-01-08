import csv
import logging
from typing import List, Dict
from datetime import datetime
from models import Recordatorio
from database import db

logger = logging.getLogger(__name__)

def exportar_recordatorios(archivo_destino: str) -> bool:
    """
    Exporta los recordatorios a un archivo CSV
    
    Args:
        archivo_destino: Ruta del archivo CSV de destino
        
    Returns:
        bool: True si la exportación fue exitosa
    """
    try:
        recordatorios = Recordatorio.query.all()
        
        with open(archivo_destino, 'w', newline='', encoding='utf-8') as archivo:
            writer = csv.writer(archivo)
            # Escribir encabezados
            writer.writerow(['nombre', 'telefono', 'fecha', 'hora', 'mensaje', 'tipo', 'repeticion'])
            
            # Escribir datos
            for r in recordatorios:
                writer.writerow([
                    r.nombre,
                    r.telefono,
                    r.fecha.strftime('%Y-%m-%d'),
                    r.hora.strftime('%H:%M'),
                    r.mensaje,
                    r.tipo,
                    r.repeticion
                ])
                
        logger.info(f"Exportación exitosa a {archivo_destino}")
        return True
        
    except Exception as e:
        logger.error(f"Error al exportar recordatorios: {str(e)}")
        return False

def importar_recordatorios(archivo_origen: str) -> tuple[bool, str]:
    """
    Importa recordatorios desde un archivo CSV
    
    Args:
        archivo_origen: Ruta del archivo CSV a importar
        
    Returns:
        tuple: (éxito, mensaje)
    """
    try:
        with open(archivo_origen, 'r', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            
            for row in reader:
                recordatorio = Recordatorio(
                    nombre=row['nombre'],
                    telefono=row['telefono'],
                    fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                    hora=datetime.strptime(row['hora'], '%H:%M').time(),
                    mensaje=row['mensaje'],
                    tipo=row['tipo'],
                    repeticion=row['repeticion']
                )
                db.session.add(recordatorio)
            
            db.session.commit()
            logger.info(f"Importación exitosa desde {archivo_origen}")
            return True, "Importación completada exitosamente"
            
    except Exception as e:
        logger.error(f"Error al importar recordatorios: {str(e)}")
        return False, f"Error en la importación: {str(e)}"
