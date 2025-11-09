from functools import wraps
from flask import request, jsonify

def validate_request(validator_class):
    """
    Decorator to validate request data
    
    Usage:
        @validate_request(UploadValidator)
        def upload():
            ...
    """
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            validator = validator_class()
            
            # Validate based on request content type
            if request.is_json:
                try:
                    json_data = request.get_json() or {}
                except Exception:
                    json_data = {}
                errors = validator.validate_json(json_data)
            elif request.files:
                errors = validator.validate_files(request.files)
            else:
                errors = validator.validate_form(request.form)
            
            if errors:
                error_message = 'Validation failed'
                if errors:
                    # Use first error as main message for better UX
                    error_message = errors[0] if isinstance(errors[0], str) else 'Validation failed'
                    if len(errors) > 1:
                        error_message += f' (and {len(errors) - 1} more error(s))'
                
                return jsonify({
                    'status': 'error',
                    'message': error_message,
                    'errors': errors
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class BaseValidator:
    """Base validator class"""
    
    def validate_json(self, data):
        """Override in subclass"""
        return []
    
    def validate_files(self, files):
        """Override in subclass"""
        return []
    
    def validate_form(self, form):
        """Override in subclass"""
        return []