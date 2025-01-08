import pytz
from datetime import datetime

ZONA_HORARIA_MADRID = pytz.timezone('Europe/Madrid')

def get_current_time():
    """Obtiene la hora actual en la zona horaria de Madrid"""
    return datetime.now(ZONA_HORARIA_MADRID)

def to_local_time(dt):
    """Convierte una fecha/hora UTC a hora local de Madrid"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(ZONA_HORARIA_MADRID)

def to_utc(dt):
    """Convierte una fecha/hora local de Madrid a UTC para almacenamiento"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = ZONA_HORARIA_MADRID.localize(dt)
    return dt.astimezone(pytz.UTC)
