# app.py
import os, logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

from routes.main_routes import main_bp
from routes.upload_routes import upload_bp
from routes.analysis_routes import analysis_bp
from routes.conversion_routes import conversion_bp
from routes.download_routes import download_bp

from middleware.error_handler import register_error_handlers
from middleware.session_manager import setup_session_manager

def create_app(config_class=Config):
    app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
    app.config.from_object(config_class)

    setup_logging(app)
    setup_extensions(app)
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
                'confirm_context': '/api/confirm-context',
                'convert': '/api/convert',
                'download': '/api/download/<project_id>',
            }
        }), 200

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'converter-api', 'version': '1.0.0'}), 200

    return app

def setup_logging(app):
    level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    log_file = app.config.get('LOG_FILE', 'app.log')
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )
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
    if app.config.get('SESSION_TYPE', 'filesystem') == 'filesystem':
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    app.logger.info('Extensions initialized')

def register_blueprints(app):
    # UI pages (root)
    app.register_blueprint(main_bp)

    # IMPORTANT: Upload without /api so /upload exists for your templates
    app.register_blueprint(upload_bp)  # -> /upload (GET + POST)

    # APIs under /api
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(conversion_bp, url_prefix='/api')
    app.register_blueprint(download_bp, url_prefix='/api')

    app.logger.info('Blueprints registered')

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)