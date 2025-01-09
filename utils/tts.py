import os
from gtts import gTTS
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

def texto_a_voz(texto: str, nombre_archivo: str = None, contexto: str = 'general') -> str:
    """
    Convierte texto a voz optimizado para diferentes contextos

    Args:
        texto: El texto a convertir en voz
        nombre_archivo: Nombre personalizado para el archivo de audio
        contexto: Tipo de mensaje ('medico', 'recordatorio', 'general')

    Returns:
        str: Ruta del archivo de audio generado
    """
    try:
        # Crear directorio para archivos de audio si no existe
        audio_dir = os.path.join('static', 'audio')
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)

        # Generar nombre de archivo único si no se proporciona uno
        if nombre_archivo is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f'mensaje_{timestamp}.mp3'

        # Ruta completa del archivo
        ruta_archivo = os.path.join(audio_dir, nombre_archivo)

        # Optimizar texto según contexto
        texto_optimizado = _optimizar_texto(texto, contexto)

        # Generar audio con configuración optimizada
        logger.debug(f"Generando audio para texto optimizado: {texto_optimizado}")
        tts = gTTS(text=texto_optimizado, lang='es', slow=(contexto in ['medico', 'recordatorio']))
        tts.save(ruta_archivo)

        logger.info(f"Audio generado exitosamente: {ruta_archivo}")
        return os.path.join('audio', nombre_archivo)

    except Exception as e:
        logger.error(f"Error al generar audio: {str(e)}")
        raise

def _optimizar_texto(texto: str, contexto: str) -> str:
    """
    Optimiza el texto para mejor comprensión según el contexto
    """
    # Limpiar espacios extras y normalizar puntuación
    texto = re.sub(r'\s+', ' ', texto).strip()
    texto = re.sub(r'([.,!?])(?=[^\s])', r'\1 ', texto)

    if contexto == 'medico':
        # Añadir pausas extra después de términos médicos
        texto = re.sub(r'([0-9]+\s*(?:mg|ml|g|mcg|UI))', r'\1. ', texto)
        # Enfatizar instrucciones importantes
        texto = texto.replace('IMPORTANTE:', 'IMPORTANTE. ')
        texto = texto.replace('ADVERTENCIA:', 'ADVERTENCIA. ')

    elif contexto == 'recordatorio':
        # Añadir pausas para fechas y horas
        texto = re.sub(r'(\d{1,2}:\d{2})', r'\1. ', texto)
        texto = re.sub(r'(\d{1,2}/\d{1,2}/\d{4})', r'\1. ', texto)

    # Añadir pausas naturales en frases largas
    texto = re.sub(r'([^.,!?]){50,}?([.,!?])', r'\1.\2', texto)

    return texto
