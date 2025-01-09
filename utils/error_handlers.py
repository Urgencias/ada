import logging
from typing import Dict, Optional, Tuple
from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

class ApiError(Exception):
    """Clase base para errores de API"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class NetelipError(ApiError):
    """Errores específicos de Netelip"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        # Mensajes amigables para errores comunes
        friendly_messages = {
            "CONNECTION_ERROR": "No pudimos conectarnos con el servicio de llamadas. Por favor, revise su conexión a internet.",
            "TIMEOUT_ERROR": "La llamada está tardando demasiado. Por favor, inténtelo de nuevo en unos momentos.",
            "AUTH_ERROR": "Hay un problema con la configuración del servicio. Por favor, contacte con soporte.",
            "FORMAT_ERROR": "El número de teléfono no es correcto. Por favor, revíselo e inténtelo de nuevo.",
            "API_ERROR": "El servicio de llamadas no está respondiendo correctamente. Por favor, espere unos minutos.",
        }

        if details and details.get('error_type') in friendly_messages:
            message = friendly_messages[details['error_type']]

        super().__init__(message, status_code, details)

def init_error_handlers(app):
    """Inicializa los manejadores de error para la aplicación"""

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        """Manejador para errores de API personalizados"""
        logger.error(f"Error de API: {error.message}")
        if request.is_json:
            response = {
                'error': True,
                'mensaje': error.message,
                'detalles': error.details
            }
            return jsonify(response), error.status_code
        return render_template('errores.html',
                            error_code=error.status_code,
                            error_message="Lo sentimos, algo no salió bien",
                            error_description=error.message), error.status_code

    @app.errorhandler(400)
    def bad_request_error(error):
        """Manejador para errores de solicitud incorrecta"""
        logger.error(f"Error 400: {error}")
        return render_template('errores.html',
                            error_code=400,
                            error_message="La información no es correcta",
                            error_description="Por favor, revise los datos ingresados e inténtelo de nuevo."), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Manejador para errores de autenticación"""
        logger.error(f"Error 401: {error}")
        return render_template('errores.html',
                            error_code=401,
                            error_message="Necesita iniciar sesión",
                            error_description="Para su seguridad, por favor inicie sesión antes de continuar."), 401

    @app.errorhandler(404)
    def not_found_error(error):
        """Manejador para errores de página no encontrada"""
        logger.error(f"Error 404: {error}")
        return render_template('errores.html',
                            error_code=404,
                            error_message="Página no encontrada",
                            error_description="Lo sentimos, la página que busca no existe. ¿Necesita ayuda para encontrar algo?"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Manejador para errores internos del servidor"""
        logger.error(f"Error 500: {error}")
        return render_template('errores.html',
                            error_code=500,
                            error_message="Hubo un problema",
                            error_description="Lo sentimos, estamos teniendo dificultades técnicas. Por favor, espere unos minutos e inténtelo de nuevo."), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Manejador global de excepciones"""
        logger.exception("Error no manejado:")

        if isinstance(error, HTTPException):
            return render_template('errores.html',
                                error_code=error.code,
                                error_message="Algo no salió como esperábamos",
                                error_description=error.description), error.code

        return render_template('errores.html',
                            error_code=500,
                            error_message="Hubo un problema inesperado",
                            error_description="Lo sentimos mucho. Por favor, inténtelo de nuevo en unos momentos."), 500

# Funciones auxiliares para el manejo de errores
def log_error(error_type: str, message: str, extra_data: Optional[Dict] = None) -> None:
    """
    Registra un error en el log con información adicional
    """
    error_info = {
        'tipo': error_type,
        'mensaje': message
    }
    if extra_data:
        error_info.update(extra_data)

    logger.error(f"Error registrado: {error_info}")

def format_error_response(message: str, details: Optional[Dict] = None) -> Tuple[Dict, int]:
    """
    Formatea una respuesta de error para APIs
    """
    response = {
        'error': True,
        'mensaje': message
    }
    if details:
        response['detalles'] = details

    return response, 400
