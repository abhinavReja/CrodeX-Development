from middleware.validation import BaseValidator

class ConversionValidator(BaseValidator):
    """Validator for conversion requests"""
    
    SUPPORTED_FRAMEWORKS = [
        'Django', 'Flask', 'FastAPI',
        'Laravel', 'Symfony', 'CodeIgniter',
        'Express.js', 'NestJS', 'Fastify',
        'Spring Boot', 'ASP.NET Core'
    ]
    
    def validate_json(self, data):
        errors = []
        
        if not data:
            errors.append('No data provided')
            return errors
        
        # Required field
        if 'target_framework' not in data:
            errors.append('Missing required field: target_framework')
        elif data['target_framework'] not in self.SUPPORTED_FRAMEWORKS:
            errors.append(f'Unsupported target framework: {data["target_framework"]}')
            errors.append(f'Supported frameworks: {", ".join(self.SUPPORTED_FRAMEWORKS)}')
        
        return errors