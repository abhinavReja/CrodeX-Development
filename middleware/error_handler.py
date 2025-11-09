from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
import traceback

def register_error_handlers(app):
    """Register application error handlers"""
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 Bad Request"""
        return jsonify({
            'status': 'error',
            'code': 400,
            'message': 'Bad request',
            'details': str(e)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        """Handle 401 Unauthorized"""
        return jsonify({
            'status': 'error',
            'code': 401,
            'message': 'Unauthorized'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden"""
        return jsonify({
            'status': 'error',
            'code': 403,
            'message': 'Access forbidden'
        }), 403
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found"""
        return jsonify({
            'status': 'error',
            'code': 404,
            'message': 'Resource not found'
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(e):
        """Handle 413 Payload Too Large"""
        return jsonify({
            'status': 'error',
            'code': 413,
            'message': 'File too large. Maximum size is 100MB.'
        }), 413
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 Internal Server Error"""
        current_app.logger.error(f"Internal server error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        return jsonify({
            'status': 'error',
            'code': 500,
            'message': 'Internal server error',
            'details': str(e) if app.debug else 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions"""
        
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e
        
        # Log the error
        current_app.logger.error(f"Unhandled exception: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        # Return generic error response
        return jsonify({
            'status': 'error',
            'code': 500,
            'message': 'An unexpected error occurred',
            'details': str(e) if app.debug else None
        }), 500