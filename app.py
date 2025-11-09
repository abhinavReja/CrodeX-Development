# app.py
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from config import Config

# Try to import Flask-Session (optional, for server-side session storage)
try:
    from flask_session import Session
    FLASK_SESSION_AVAILABLE = True
except ImportError:
    FLASK_SESSION_AVAILABLE = False
    Session = None

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

from routes.main_routes import main_bp
from routes.upload_routes import upload_bp
from routes.analysis_routes import analysis_bp
from routes.conversion_routes import conversion_bp
# Download routes imported below where needed

from middleware.error_handler import register_error_handlers
from middleware.session_manager import setup_session_manager

# Import services for file handling
from services.analyzer import FrameworkAnalyzer
from services.file_counter import FileCounter
from utils.cleanup_manager import CleanupManager
from utils.file_manager import FileManager

def create_app(config_class=Config):
    app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
    app.config.from_object(config_class)

    setup_logging(app)
    setup_extensions(app)
    
    # Initialize services (file handling utilities)
    setup_services(app)
    
    # Register blueprints
    register_blueprints(app)
    register_error_handlers(app)
    setup_session_manager(app)

    # Optional: API index + health
    @app.route('/api/', methods=['GET'])
    def api_index():
        return jsonify({
            'status': 'ok',
            'endpoints': {
                'upload': '/upload',
                'analyze': '/api/analyze',
                'file_analysis': '/api/file-analysis/<project_id>',
                'confirm_context': '/api/confirm-context',
                'convert': '/api/convert',
                'conversion_progress': '/api/conversion-progress/<project_id>',
                'download': '/api/download/<project_id>',
                'zip_structure': '/api/zip-structure/<project_id>',
            }
        }), 200

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'converter-api', 'version': '1.0.0'}), 200

    return app

def setup_logging(app):
    import sys
    level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    log_file = app.config.get('LOG_FILE', 'app.log')
    
    # Configure file handler with UTF-8 encoding to handle special characters (especially on Windows)
    if sys.platform == 'win32':
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    else:
        file_handler = logging.FileHandler(log_file)
    
    # Configure stream handler (stdout) with error handling for Unicode
    stream_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    # Configure root logger (clear existing handlers first to avoid duplicates)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    
    app.logger.setLevel(level)
    app.logger.info('Application logging configured')

def setup_extensions(app):
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Disposition"],
            "supports_credentials": True
        }
    })
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Flask-Session for server-side session storage (if available)
    # This stores sessions on disk instead of in cookies, avoiding cookie size limits
    if FLASK_SESSION_AVAILABLE and Session:
        if app.config.get('SESSION_TYPE', 'filesystem') == 'filesystem':
            os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
            # Initialize Flask-Session to use filesystem storage (stores sessions on disk, not in cookies)
            Session(app)
            app.logger.info('Flask-Session initialized with filesystem storage')
        else:
            # For other session types (e.g., redis), initialize Session
            Session(app)
            app.logger.info(f'Flask-Session initialized with {app.config.get("SESSION_TYPE")} storage')
    else:
        app.logger.warning('Flask-Session not available. Sessions will use cookie-based storage (may have size limits). Install flask-session to use server-side storage.')
        # Ensure session directory exists even without Flask-Session
        if app.config.get('SESSION_TYPE', 'filesystem') == 'filesystem':
            os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    app.logger.info('Extensions initialized')

def setup_services(app):
    """Initialize shared file-handling services and attach them to the app."""
    
    upload_folder = app.config['UPLOAD_FOLDER']
    
    file_manager = FileManager(upload_folder)
    cleanup_manager = CleanupManager(upload_folder)
    framework_analyzer = FrameworkAnalyzer()
    file_counter = FileCounter()
    
    # Store in app.extensions for blueprint access
    app.extensions['file_manager'] = file_manager
    app.extensions['cleanup_manager'] = cleanup_manager
    app.extensions['framework_analyzer'] = framework_analyzer
    app.extensions['file_counter'] = file_counter
    
    # Perform a light cleanup on startup (best-effort)
    try:
        cleanup_manager.cleanup_old_projects()
        app.logger.info('Startup cleanup completed')
    except Exception as exc:  # pylint: disable=broad-except
        app.logger.warning('Initial cleanup skipped: %s', exc)

def register_blueprints(app):
    # UI pages (root)
    app.register_blueprint(main_bp)

    # IMPORTANT: Upload without /api so /upload exists for your templates
    app.register_blueprint(upload_bp)  # -> /upload (GET + POST)
    
    # Register template routes without /api prefix
    from routes.analysis_routes import context_form
    from routes.conversion_routes import progress_page
    from routes.upload_routes import get_zip_structure
    app.add_url_rule('/context/<project_id>', 'analysis.context_form', context_form, methods=['GET', 'POST'])
    app.add_url_rule('/progress/<project_id>', 'conversion.progress_page', progress_page, methods=['GET'])

    # Register download template route (without /api prefix for page access)
    from routes.download_routes import download_file
    app.add_url_rule('/download/<project_id>', 'download.download_file', download_file, methods=['GET'])
    
    # APIs under /api
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(conversion_bp, url_prefix='/api')
    
    # Register api_download blueprint for download API routes
    from routes.download_routes import api_download_bp
    app.register_blueprint(api_download_bp, url_prefix='/api')
    
    # Register zip-structure API endpoint with /api prefix
    app.add_url_rule('/api/zip-structure/<project_id>', 'upload.get_zip_structure', get_zip_structure, methods=['GET'])

    app.logger.info('Blueprints registered')

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)