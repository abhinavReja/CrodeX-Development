from middleware.validation import BaseValidator

class UploadValidator(BaseValidator):
    """Validator for upload requests"""
    
    def validate_files(self, files):
        errors = []
        
        if 'file' not in files:
            errors.append('No file provided')
            return errors
        
        file = files['file']
        
        if file.filename == '':
            errors.append('No file selected')
        
        # Check file extension
        allowed_extensions = {'zip', 'tar', 'gz'}
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            errors.append('Invalid file type. Only ZIP files are allowed.')
        
        return errors