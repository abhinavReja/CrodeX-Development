import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_sessions')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = True  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp', 'uploads')
    ALLOWED_EXTENSIONS = {'zip', 'tar', 'gz', 'rar'}
    
    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Gemini API configuration (supports both GEMINI_API_KEY and ANTHROPIC_API_KEY for backward compatibility)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')  # Kept for backward compatibility
    
    # Cleanup configuration
    CLEANUP_INTERVAL_HOURS = 2
    MAX_PROJECT_AGE_HOURS = 4
    
    # Rate limiting (optional)
    RATELIMIT_ENABLED = False
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'app.log'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_TYPE = 'redis'  # Use Redis in production
    SESSION_REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379')
    RATELIMIT_ENABLED = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SESSION_TYPE = 'filesystem'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp', 'test_uploads')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}