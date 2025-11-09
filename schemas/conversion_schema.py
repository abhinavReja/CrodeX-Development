from middleware.validation import BaseValidator

class ConversionValidator(BaseValidator):
    """Validator for conversion requests
    
    Note: target_framework is optional in request body since it can be retrieved
    from session context. The route handler will validate it properly.
    """
    
    SUPPORTED_FRAMEWORKS = [
        'Django', 'Flask', 'FastAPI',
        'Laravel', 'Symfony', 'CodeIgniter',
        'Express.js', 'NestJS', 'Fastify',
        'Spring Boot', 'ASP.NET Core'
    ]
    
    def validate_json(self, data):
        errors = []
        
        # Allow empty data - target_framework can come from session context
        if not data:
            return errors  # Empty data is OK, route will check session
        
        # If target_framework is provided, validate it
        if 'target_framework' in data and data['target_framework']:
            if data['target_framework'] not in self.SUPPORTED_FRAMEWORKS:
                errors.append(f'Unsupported target framework: {data["target_framework"]}')
                errors.append(f'Supported frameworks: {", ".join(self.SUPPORTED_FRAMEWORKS)}')
        
        return errors