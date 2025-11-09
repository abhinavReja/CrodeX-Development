import os
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import Config
import logging
from datetime import timedelta

# Get the directory where this app.py file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Import routes - handle both old and new structure
from routes.main_routes import main_bp

# Try to import template and API blueprints separately
try:
    from routes.upload_routes import upload_bp, api_upload_bp
except ImportError:
    from routes.upload_routes import upload_bp
    api_upload_bp = None

try:
    from routes.analysis_routes import analysis_bp, api_analysis_bp
except ImportError:
    from routes.analysis_routes import analysis_bp
    api_analysis_bp = None

try:
    from routes.conversion_routes import conversion_bp, api_conversion_bp
except ImportError:
    from routes.conversion_routes import conversion_bp
    api_conversion_bp = None

# Download routes - these should always be available with key API changes
from routes.download_routes import download_bp, api_download_bp

# Import middleware
from middleware.error_handler import register_error_handlers
from middleware.session_manager import setup_session_manager

def create_app(config_class=Config):
    """
    Application Factory Pattern
    Creates and configures Flask application
    """
    
    # Initialize Flask app
    app = Flask(__name__, 
                template_folder=TEMPLATE_DIR,
                static_folder=STATIC_DIR)
    app.config.from_object(config_class)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize extensions
    setup_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup session manager
    setup_session_manager(app)
    
    return app

def setup_logging(app):
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application logging configured')

def setup_extensions(app):
    """Initialize Flask extensions"""
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Disposition"],
            "supports_credentials": True
        }
    })
    
    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    app.logger.info('Extensions initialized')

def register_blueprints(app):
    """Register application blueprints"""
    
    # Register main routes (no prefix)
    app.register_blueprint(main_bp)
    
    # Register template routes (no prefix) - for rendering HTML pages
    # Only register if they exist
    try:
        app.register_blueprint(upload_bp)  # /upload
    except:
        pass
    
    try:
        app.register_blueprint(analysis_bp)  # /analysis/<file_id>, /context/<file_id>
    except:
        pass
    
    try:
        app.register_blueprint(conversion_bp)  # /progress/<task_id>
    except:
        pass
    
    app.register_blueprint(download_bp)  # /download/<file_id>
    
    # Register API routes with /api prefix
    # Only register if they exist
    if api_upload_bp:
        app.register_blueprint(api_upload_bp, url_prefix='/api')  # /api/upload, /api/zip-structure
    
    if api_analysis_bp:
        app.register_blueprint(api_analysis_bp, url_prefix='/api')  # /api/analyze, /api/autocomplete, /api/confirm-context
    
    if api_conversion_bp:
        app.register_blueprint(api_conversion_bp, url_prefix='/api')  # /api/progress, /api/progress/stream, /api/convert, /api/cancel
    
    # Download API blueprint - always register (key API change)
    app.register_blueprint(api_download_bp, url_prefix='/api')  # /api/download
    
    app.logger.info('Blueprints registered')

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
