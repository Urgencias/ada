from flask import Flask
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

def init_routes(app: Flask):
    """Initialize all routes for the application"""
    logger.info("Inicializando rutas de la aplicación")

    # Import routes here to avoid circular imports
    from .auth import auth_bp
    from .main import main_bp, init_scheduled_calls_checker
    from .notificaciones import notificaciones_bp
    from .test_calls import test_calls_bp

    # Register blueprints with their prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)  # Registrar como 'main' sin nombre personalizado
    app.register_blueprint(notificaciones_bp)  # Sin prefix para mantener las rutas simples
    app.register_blueprint(test_calls_bp, url_prefix='/test')

    # Initialize call checker after blueprints are registered
    init_scheduled_calls_checker(app)

    logger.info("Rutas inicializadas correctamente")
