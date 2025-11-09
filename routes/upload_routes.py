from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from schemas.upload_schema import UploadValidator
from middleware.validation import validate_request
from services.claude_api import ClaudeService
from utils.file_manager import FileManager
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
@validate_request(UploadValidator)
def upload_project():
    """
    Upload and extract project ZIP file
    
    Request:
        - file: ZIP file (multipart/form-data)
        
    Response:
        {
            "status": "success",
            "project_id": "uuid",
            "message": "Project uploaded successfully",
            "file_info": {
                "filename": "project.zip",
                "size": 1024000,
                "files_count": 45
            }
        }
    """
    
    try:
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Invalid file type. Only ZIP files are allowed.'
            }), 400
        
        # Generate unique project ID
        project_id = str(uuid.uuid4())
        
        # Initialize file manager
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        
        # Create project directory
        project_path = file_manager.create_project_directory(project_id)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(project_path, filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Extract ZIP file
        extracted_path = file_manager.extract_zip(file_path, project_path)
        
        # Count extracted files
        files_count = file_manager.count_files(extracted_path)
        
        # Load file contents
        files_dict = file_manager.load_files(extracted_path)
        
        # Store in session
        session['project_id'] = project_id
        session['project_path'] = project_path
        session['extracted_path'] = extracted_path
        session['upload_timestamp'] = datetime.now().isoformat()
        session['files_dict'] = files_dict  # Store for later use
        session.modified = True
        
        # Log upload
        current_app.logger.info(f"Project uploaded: {project_id} - {files_count} files")
        
        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'message': 'Project uploaded successfully',
            'file_info': {
                'filename': filename,
                'size': file_size,
                'files_count': files_count
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']