import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Babel configuration for internationalization
    BABEL_DEFAULT_LOCALE = 'en'  # Changed to English by default
    BABEL_DEFAULT_TIMEZONE = 'America/New_York'  # Default US timezone

    # Available languages
    LANGUAGES = {
        'en': 'English',
        'es': 'Español'
    }

    # Timezone configurations for US regions
    TIMEZONE_CONFIG = {
        'US': {
            'ET': 'America/New_York',
            'CT': 'America/Chicago',
            'MT': 'America/Denver',
            'PT': 'America/Los_Angeles'
        },
        'ES': 'Europe/Madrid'
    }

    # Phone number formats
    PHONE_FORMAT = {
        'US': '+1 (XXX) XXX-XXXX',
        'ES': '+34 XXX XXX XXX'
    }

    # Call providers configuration
    CALL_PROVIDERS = {
        'US': ['twilio'],  # Twilio as primary provider for US
        'ES': ['netelip']  # Keep Netelip for Spain
    }

    # Duration settings optimized for elderly care
    MIN_CALL_DURATION = 20  # Increased for better comprehension
    MAX_RETRIES = 3
    RETRY_DELAY = 10  # Increased delay between retries

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    # Accessibility settings
    ACCESSIBILITY_CONFIG = {
        'LARGE_FONT': True,
        'HIGH_CONTRAST': True,
        'SIMPLIFIED_INTERFACE': True,
        'VOICE_FEEDBACK': True
    }

    # Instance identification for multi-deployment
    INSTANCE_NAME = os.environ.get('INSTANCE_NAME', 'default')
    INSTANCE_TYPE = os.environ.get('INSTANCE_TYPE', 'community')  # community/healthcare/personal