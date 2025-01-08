import os
from flask import Flask
from extensions import db, init_extensions
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-12345')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions (including Flask-Login)
    init_extensions(app)

    with app.app_context():
        try:
            # Import models to ensure they're registered with SQLAlchemy
            from models import User, Recordatorio, RegistroLlamada

            # Initialize routes after database is configured
            from routes import init_routes
            init_routes(app)  # This will register all blueprints

            # Create tables if they don't exist
            db.create_all()

            # Ensure admin user exists
            admin = User.query.filter_by(email='admin@urgencias-ia.com').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@urgencias-ia.com',
                    es_admin=True,
                    email_verificado=True,
                    pago_verificado=True
                )
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info(f"Admin user created: {admin.email}")
            else:
                logger.info("Admin user already exists")

        except Exception as e:
            logger.error(f"Error in app initialization: {str(e)}")
            logger.exception("Full traceback:")
            raise

    return app