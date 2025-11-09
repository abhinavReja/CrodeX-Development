from middleware.validation import BaseValidator

class ContextValidator(BaseValidator):
    """Validator for context confirmation requests"""
    
    def validate_json(self, data):
        errors = []
        
        if not data:
            errors.append('No data provided')
            return errors
        
        # Required fields
        required_fields = ['purpose', 'features', 'business_logic']
        
        for field in required_fields:
            if field not in data:
                errors.append(f'Missing required field: {field}')
            elif not data[field]:
                errors.append(f'Field "{field}" cannot be empty')
        
        # Validate features is a list
        if 'features' in data and not isinstance(data['features'], list):
            errors.append('Features must be a list')
        
        return errors