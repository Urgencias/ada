import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf import CSRFProtect

# Configurar logging básico
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to app yet
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

def init_extensions(app):
    """Initialize all Flask extensions"""
    try:
        logger.info("Inicializando extensiones de Flask")

        # Initialize extensions with app
        db.init_app(app)
        login_manager.init_app(app)
        csrf.init_app(app)

        # Configure login manager
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
        login_manager.login_message_category = 'info'

        @login_manager.user_loader
        def load_user(user_id):
            try:
                # Import User model here to avoid circular imports
                from models import User
                return User.query.get(int(user_id))
            except Exception as e:
                logger.error(f"Error al cargar usuario: {str(e)}")
                return None

        logger.info("Extensiones inicializadas correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar extensiones: {str(e)}")
        logger.exception("Stacktrace completo:")
        return False
